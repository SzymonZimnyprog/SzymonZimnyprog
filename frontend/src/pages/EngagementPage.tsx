import { useState } from "react";
import {
  downloadExport,
  montecarloEngagement,
  salvoEngagement,
  simulateEngagement,
  solveEngagement,
  type EngagementRequest,
  type EngagementResult,
  type FireSolution,
  type MonteCarloResult,
  type SalvoResult,
} from "../api";
import { defaultEngagement } from "../defaults";
import LineChart from "../components/LineChart";
import TrajectoryPlot from "../components/TrajectoryPlot";
import PathPlot from "../components/PathPlot";
import NumberField from "../components/NumberField";

export default function EngagementPage() {
  const [req, setReq] = useState<EngagementRequest>(
    structuredClone(defaultEngagement)
  );
  const [result, setResult] = useState<EngagementResult | null>(null);
  const [solution, setSolution] = useState<FireSolution | null>(null);
  const [salvo, setSalvo] = useState<SalvoResult | null>(null);
  const [salvoCount, setSalvoCount] = useState(3);
  const [mc, setMc] = useState<MonteCarloResult | null>(null);
  const [trials, setTrials] = useState(150);
  const [posSigma, setPosSigma] = useState(300);
  const [velSigma, setVelSigma] = useState(25);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const it = req.interceptor;
  const tg = req.target;
  const g = it.motor.grain;

  function patchInt(part: Partial<EngagementRequest["interceptor"]>) {
    setReq((r) => ({ ...r, interceptor: { ...r.interceptor, ...part } }));
  }
  function patchTgt(part: Partial<EngagementRequest["target"]>) {
    setReq((r) => ({ ...r, target: { ...r.target, ...part } }));
  }
  function setTgtVec(key: "position" | "velocity", idx: number, v: number) {
    setReq((r) => {
      const vec = [...r.target[key]];
      vec[idx] = v;
      return { ...r, target: { ...r.target, [key]: vec } };
    });
  }

  async function run() {
    setBusy(true);
    setError(null);
    setSolution(null);
    setSalvo(null);
    try {
      setResult(await simulateEngagement(req));
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  }

  function saveScenario() {
    const blob = new Blob([JSON.stringify(req, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "engagement_scenario.json";
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
  }

  function loadScenario(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = () => {
      try {
        setReq(JSON.parse(String(reader.result)) as EngagementRequest);
        setResult(null);
        setSolution(null);
        setError(null);
      } catch {
        setError("Invalid scenario file.");
      }
    };
    reader.readAsText(file);
    e.target.value = "";
  }

  async function runMonteCarlo() {
    setBusy(true);
    setError(null);
    try {
      setMc(
        await montecarloEngagement({
          engagement: req,
          trials,
          position_sigma: posSigma,
          velocity_sigma: velSigma,
          seed: 0,
        })
      );
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  }

  async function fireSalvo() {
    setBusy(true);
    setError(null);
    try {
      setSalvo(
        await salvoEngagement({
          engagement: req,
          count: salvoCount,
          stagger: 1.5,
          elevation_spread: 8,
          auto_aim: true,
        })
      );
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  }

  async function solve() {
    setBusy(true);
    setError(null);
    setSalvo(null);
    try {
      const sol = await solveEngagement(req);
      setSolution(sol);
      setResult(sol.engagement);
      patchInt({
        elevation_deg: Math.round(sol.elevation_deg * 10) / 10,
        azimuth_deg: Math.round(sol.azimuth_deg * 10) / 10,
      });
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  }

  const intGround = result?.interceptor_position.map((p) => Math.hypot(p[0], p[1])) ?? [];
  const intAlt = result?.interceptor_position.map((p) => p[2]) ?? [];
  const tgtGround = result?.target_position.map((p) => Math.hypot(p[0], p[1])) ?? [];
  const tgtAlt = result?.target_position.map((p) => p[2]) ?? [];
  const s = result?.summary;
  const marker = s
    ? {
        ground: Math.hypot(s.intercept_point[0], s.intercept_point[1]),
        alt: s.intercept_point[2],
        label: s.intercepted ? "Intercept" : "Closest approach",
      }
    : null;

  return (
    <div className="page">
      <h2>Interception engagement</h2>
      <p className="muted">
        Proportional-navigation homing (aᵪ = N·V_c·λ̇) of a boosting interceptor
        against a ballistic target. Kinematic intercept criterion — closest
        approach inside the lethal radius.
      </p>

      <div className="layout">
        <section className="params">
          <h3>Interceptor</h3>
          <div className="grid">
            <NumberField label="Elevation" unit="°" step={1} min={0} max={90} value={it.elevation_deg}
              onChange={(v) => patchInt({ elevation_deg: v })} />
            <NumberField label="Azimuth" unit="°" step={1} value={it.azimuth_deg}
              onChange={(v) => patchInt({ azimuth_deg: v })} />
            <NumberField label="Nav const N" step={0.5} min={2} max={6} value={it.nav_constant}
              onChange={(v) => patchInt({ nav_constant: v })} />
            <NumberField label="Max lateral" unit="g" step={5} value={it.max_lateral_g}
              onChange={(v) => patchInt({ max_lateral_g: v })} />
            <NumberField label="Seeker range" unit="m" step={1000} value={it.seeker_range}
              onChange={(v) => patchInt({ seeker_range: v })} />
            <NumberField label="Seeker boresight σ" unit="mrad" step={1} min={0}
              value={it.seeker_angular_noise}
              onChange={(v) => patchInt({ seeker_angular_noise: v })} />
            <NumberField label="Seeker range σ" unit="frac" step={0.01} min={0}
              value={it.seeker_range_noise}
              onChange={(v) => patchInt({ seeker_range_noise: v })} />
            <NumberField label="Seeker rate" unit="Hz" step={5} min={0}
              value={it.seeker_update_rate}
              onChange={(v) => patchInt({ seeker_update_rate: v })} />
            <NumberField label="Dry mass" unit="kg" step={1} value={it.airframe.dry_mass}
              onChange={(v) => patchInt({ airframe: { ...it.airframe, dry_mass: v } })} />
          </div>
          <h4>Boost motor grain</h4>
          <div className="grid">
            <NumberField label="Outer dia" unit="m" value={g.outer_diameter}
              onChange={(v) => patchInt({ motor: { ...it.motor, grain: { ...g, outer_diameter: v } } })} />
            <NumberField label="Core dia" unit="m" value={g.core_diameter}
              onChange={(v) => patchInt({ motor: { ...it.motor, grain: { ...g, core_diameter: v } } })} />
            <NumberField label="Segment len" unit="m" value={g.segment_length}
              onChange={(v) => patchInt({ motor: { ...it.motor, grain: { ...g, segment_length: v } } })} />
            <NumberField label="Segments" step={1} min={1} value={g.segments}
              onChange={(v) => patchInt({ motor: { ...it.motor, grain: { ...g, segments: Math.round(v) } } })} />
          </div>

          <h3>Target</h3>
          <div className="grid">
            <NumberField label="Pos X (E)" unit="m" step={500} value={tg.position[0]}
              onChange={(v) => setTgtVec("position", 0, v)} />
            <NumberField label="Pos Y (N)" unit="m" step={500} value={tg.position[1]}
              onChange={(v) => setTgtVec("position", 1, v)} />
            <NumberField label="Pos Z (alt)" unit="m" step={500} value={tg.position[2]}
              onChange={(v) => setTgtVec("position", 2, v)} />
            <NumberField label="Vel X" unit="m/s" step={10} value={tg.velocity[0]}
              onChange={(v) => setTgtVec("velocity", 0, v)} />
            <NumberField label="Vel Y" unit="m/s" step={10} value={tg.velocity[1]}
              onChange={(v) => setTgtVec("velocity", 1, v)} />
            <NumberField label="Vel Z" unit="m/s" step={10} value={tg.velocity[2]}
              onChange={(v) => setTgtVec("velocity", 2, v)} />
            <NumberField label="Mass" unit="kg" step={10} value={tg.mass}
              onChange={(v) => patchTgt({ mass: v })} />
            <NumberField label="Lethal radius" unit="m" step={1} value={req.lethal_radius}
              onChange={(v) => setReq((r) => ({ ...r, lethal_radius: v }))} />
          </div>

          <button className="run" onClick={run} disabled={busy}>
            {busy ? "Simulating…" : "Run engagement"}
          </button>
          <button className="run secondary" onClick={solve} disabled={busy}>
            {busy ? "Solving…" : "Auto-aim — compute firing solution"}
          </button>
          <div className="salvo-row">
            <NumberField label="Salvo shots" step={1} min={1} max={8} value={salvoCount}
              onChange={(v) => setSalvoCount(Math.max(1, Math.min(8, Math.round(v))))} />
            <button className="run secondary" onClick={fireSalvo} disabled={busy}>
              {busy ? "Firing…" : "Fire salvo (layered)"}
            </button>
          </div>

          <h3>Monte-Carlo Pk (track uncertainty)</h3>
          <div className="grid">
            <NumberField label="Trials" step={10} min={10} max={1000} value={trials}
              onChange={(v) => setTrials(Math.max(10, Math.min(1000, Math.round(v))))} />
            <NumberField label="Pos σ" unit="m" step={50} value={posSigma}
              onChange={(v) => setPosSigma(Math.max(0, v))} />
            <NumberField label="Vel σ" unit="m/s" step={5} value={velSigma}
              onChange={(v) => setVelSigma(Math.max(0, v))} />
          </div>
          <button className="run secondary" onClick={runMonteCarlo} disabled={busy}>
            {busy ? "Running…" : "Run Monte-Carlo"}
          </button>
          <div className="export-row" style={{ marginTop: "0.6rem" }}>
            <button onClick={saveScenario}>Save scenario</button>
            <label className="filebtn">
              Load scenario
              <input type="file" accept="application/json" onChange={loadScenario} hidden />
            </label>
          </div>
          {error && <p className="error">{error}</p>}
        </section>

        <section className="results">
          {s && (
            <>
              <div className={`verdict ${s.intercepted ? "hit" : "miss"}`}>
                {s.intercepted ? "✓ INTERCEPT" : "✗ MISS"}
                <span>
                  miss {s.miss_distance.toFixed(1)} m · t {s.intercept_time.toFixed(2)} s ·
                  closing {Math.abs(s.closing_speed_at_intercept).toFixed(0)} m/s
                </span>
              </div>

              {solution && (
                <div className="solution">
                  <strong>Firing solution</strong>
                  <span>
                    elevation {solution.elevation_deg.toFixed(1)}° · azimuth{" "}
                    {solution.azimuth_deg.toFixed(1)}° (form fields updated)
                  </span>
                </div>
              )}

              <TrajectoryPlot
                paths={[
                  { label: "Interceptor", color: "#6366f1", ground: intGround, alt: intAlt },
                  { label: "Target", color: "#dc2626", ground: tgtGround, alt: tgtAlt },
                ]}
                marker={marker}
              />
              <PathPlot
                xlabel="East"
                ylabel="North"
                unit="km"
                scale={1000}
                paths={[
                  {
                    label: "Interceptor",
                    color: "#6366f1",
                    x: result!.interceptor_position.map((p) => p[0]),
                    y: result!.interceptor_position.map((p) => p[1]),
                  },
                  {
                    label: "Target",
                    color: "#dc2626",
                    x: result!.target_position.map((p) => p[0]),
                    y: result!.target_position.map((p) => p[1]),
                  },
                ]}
                marker={
                  s.intercept_point.length
                    ? { x: s.intercept_point[0], y: s.intercept_point[1], label: marker?.label ?? "" }
                    : null
                }
              />
              <LineChart
                xlabel="Time (s)"
                ylabel="Separation (m)"
                series={[{ label: "Separation", color: "#0891b2", x: result!.time, y: result!.separation }]}
              />
              <LineChart
                xlabel="Time (s)"
                ylabel="Speed (m/s)"
                series={[
                  { label: "Interceptor", color: "#6366f1", x: result!.time, y: result!.interceptor_speed },
                  { label: "Target", color: "#dc2626", x: result!.time, y: result!.target_speed },
                ]}
              />

              {solution && solution.envelope.length > 1 && (
                <LineChart
                  xlabel="Launch elevation (°)"
                  ylabel="Miss distance (m)"
                  series={[{
                    label: "Miss vs elevation",
                    color: "#7c3aed",
                    x: solution.envelope.map((e) => e.elevation),
                    y: solution.envelope.map((e) => Math.min(e.miss, 5000)),
                  }]}
                />
              )}

              <h3>Export</h3>
              <div className="export-row">
                <button onClick={() => downloadExport("/export/simulink/engagement.csv", req, "engagement.csv")}>
                  Engagement CSV
                </button>
                <button onClick={() => downloadExport("/export/simulink/driver.m", null, "szymon_sim_driver.m")}>
                  MATLAB driver
                </button>
              </div>
            </>
          )}
          {salvo && (
            <>
              <div className={`verdict ${salvo.intercepted ? "hit" : "miss"}`}>
                {salvo.intercepted ? "✓ TARGET NEUTRALISED" : "✗ LEAKER"}
                <span>
                  {salvo.hits}/{salvo.count} hits · Pk {(salvo.success_fraction * 100).toFixed(0)}% ·
                  best miss {salvo.best_miss.toFixed(1)} m · azimuth {salvo.azimuth_deg.toFixed(1)}°
                </span>
              </div>
              <table className="shots">
                <thead>
                  <tr>
                    <th>#</th>
                    <th>Launch t</th>
                    <th>Elevation</th>
                    <th>Miss</th>
                    <th>Result</th>
                  </tr>
                </thead>
                <tbody>
                  {salvo.shots.map((sh) => (
                    <tr key={sh.index} className={sh.intercepted ? "hit" : ""}>
                      <td>{sh.index + 1}</td>
                      <td>{sh.launch_time.toFixed(1)} s</td>
                      <td>{sh.elevation_deg.toFixed(1)}°</td>
                      <td>{sh.miss_distance.toFixed(1)} m</td>
                      <td>{sh.intercepted ? "HIT" : "miss"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </>
          )}

          {mc && (
            <>
              <div className={`verdict ${mc.pk >= 0.8 ? "hit" : "miss"}`}>
                Pk {(mc.pk * 100).toFixed(0)}%
                <span>
                  {mc.hits}/{mc.trials} kills · mean miss {mc.mean_miss.toFixed(1)} m ·
                  median {mc.median_miss.toFixed(1)} m · p90 {mc.p90_miss.toFixed(1)} m
                </span>
              </div>
              <LineChart
                xlabel="Miss distance (m)"
                ylabel="Trials"
                series={[{
                  label: "Miss histogram",
                  color: "#7c3aed",
                  x: mc.histogram_counts.map(
                    (_, i) => 0.5 * (mc.histogram_edges[i] + mc.histogram_edges[i + 1])
                  ),
                  y: mc.histogram_counts,
                }]}
              />
            </>
          )}

          {!s && !salvo && !mc && (
            <p className="muted">Configure the scenario and run the engagement.</p>
          )}
        </section>
      </div>
    </div>
  );
}
