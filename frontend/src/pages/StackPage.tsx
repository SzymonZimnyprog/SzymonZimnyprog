import { useState } from "react";
import {
  simulateMultiStage,
  flyStack,
  type GrainType,
  type Stage,
  type StackResult,
  type StagedTrajectoryResult,
  type Airframe,
} from "../api";
import { APCP, KNSB, defaultStack } from "../defaults";
import LineChart from "../components/LineChart";
import TrajectoryPlot from "../components/TrajectoryPlot";
import NumberField from "../components/NumberField";

interface LocalStage extends Stage {
  structural_mass: number;
}

const DEFAULT_PAYLOAD: Airframe = { diameter: 0.14, cd0: 0.35, dry_mass: 30 };

function initStages(): LocalStage[] {
  return structuredClone(defaultStack).map((s) => ({ ...s, structural_mass: 5 }));
}

function groundRangeAt(
  time: number[],
  position: number[][],
  sepTime: number
): number {
  let best = 0;
  let bestDist = Infinity;
  for (let i = 0; i < time.length; i++) {
    const d = Math.abs(time[i] - sepTime);
    if (d < bestDist) {
      bestDist = d;
      best = i;
    }
  }
  const pos = position[best];
  return Math.sqrt(pos[0] ** 2 + pos[1] ** 2);
}

export default function StackPage() {
  const [stages, setStages] = useState<LocalStage[]>(initStages);
  const [result, setResult] = useState<StackResult | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [payload, setPayload] = useState<Airframe>({ ...DEFAULT_PAYLOAD });
  const [launchSpeed, setLaunchSpeed] = useState(30);
  const [elevationDeg, setElevationDeg] = useState(80);
  const [azimuthDeg, setAzimuthDeg] = useState(0);
  const [dropLast, setDropLast] = useState(false);
  const [flightResult, setFlightResult] = useState<StagedTrajectoryResult | null>(null);
  const [flyBusy, setFlyBusy] = useState(false);
  const [flyError, setFlyError] = useState<string | null>(null);

  function updateStage(i: number, mut: (s: LocalStage) => LocalStage) {
    setStages((prev) => prev.map((s, j) => (j === i ? mut(structuredClone(s)) : s)));
  }

  function addStage() {
    if (stages.length >= 5) return;
    setStages((prev) => [
      ...prev,
      { ...structuredClone(defaultStack[1]), structural_mass: 5 },
    ]);
  }

  function removeStage(i: number) {
    setStages((prev) => prev.filter((_, j) => j !== i));
  }

  async function run() {
    setBusy(true);
    setError(null);
    try {
      setResult(await simulateMultiStage(stages));
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  }

  async function fly() {
    setFlyBusy(true);
    setFlyError(null);
    try {
      setFlightResult(
        await flyStack({
          stages: stages.map((s) => ({
            motor: s.motor,
            ignition_delay: s.ignition_delay,
            structural_mass: s.structural_mass,
          })),
          payload,
          launch_speed: launchSpeed,
          elevation_deg: elevationDeg,
          azimuth_deg: azimuthDeg,
          drop_last_stage: dropLast,
          dt: 0.02,
          max_time: 600,
        })
      );
    } catch (e) {
      setFlyError(String(e));
    } finally {
      setFlyBusy(false);
    }
  }

  function exportCsv() {
    if (!result) return;
    const rows = ["time_s,thrust_N"];
    for (let i = 0; i < result.time.length; i++) {
      rows.push(`${result.time[i].toFixed(4)},${result.thrust[i].toFixed(3)}`);
    }
    const blob = new Blob([rows.join("\n") + "\n"], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "stack_thrust.csv";
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
  }

  function exportFlightCsv() {
    if (!flightResult) return;
    const rows = ["time_s,altitude_m,speed_ms,mach,mass_kg"];
    for (let i = 0; i < flightResult.time.length; i++) {
      rows.push(
        `${flightResult.time[i].toFixed(3)},${flightResult.altitude[i].toFixed(1)},` +
          `${flightResult.speed[i].toFixed(2)},${flightResult.mach[i].toFixed(4)},` +
          `${flightResult.mass[i].toFixed(3)}`
      );
    }
    const blob = new Blob([rows.join("\n") + "\n"], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "staged_flight.csv";
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
  }

  const s = result?.summary;
  const fs = flightResult?.summary;

  const groundRange = flightResult
    ? flightResult.position.map((p) => Math.sqrt(p[0] ** 2 + p[1] ** 2))
    : [];

  const sepMarkers = flightResult
    ? flightResult.separations.map((ev, i) => ({
        ground: groundRangeAt(flightResult.time, flightResult.position, ev.time),
        alt: ev.altitude,
        label: `S${i + 1} drop`,
      }))
    : [];

  return (
    <div className="page">
      <h2>Multi-stage motor stack</h2>
      <p className="muted">
        Sequential stages (boost → sustain): each stage ignites after the
        previous burns out plus its coast delay. <strong>Run stack</strong> shows
        the combined thrust profile; <strong>Fly stack</strong> integrates the
        staged flight and jettisons spent-stage mass at each burnout.
      </p>

      <div className="layout">
        <section className="params">
          {stages.map((stage, i) => {
            const g = stage.motor.grain;
            const n = stage.motor.nozzle;
            return (
              <div key={i} className="stage-card">
                <div className="stage-head">
                  <strong>Stage {i + 1}</strong>
                  <div className="preset-row">
                    <button
                      onClick={() =>
                        updateStage(i, (st) => ({
                          ...st,
                          motor: { ...st.motor, propellant: { ...KNSB } },
                        }))
                      }
                    >
                      KNSB
                    </button>
                    <button
                      onClick={() =>
                        updateStage(i, (st) => ({
                          ...st,
                          motor: { ...st.motor, propellant: { ...APCP } },
                        }))
                      }
                    >
                      APCP
                    </button>
                    {stages.length > 1 && (
                      <button className="danger" onClick={() => removeStage(i)}>
                        ✕
                      </button>
                    )}
                  </div>
                </div>
                <label className="field">
                  <span className="field-label">Grain type</span>
                  <select
                    value={g.grain_type}
                    onChange={(e) =>
                      updateStage(i, (st) => ({
                        ...st,
                        motor: {
                          ...st.motor,
                          grain: {
                            ...st.motor.grain,
                            grain_type: e.target.value as GrainType,
                          },
                        },
                      }))
                    }
                  >
                    <option value="BATES">BATES</option>
                    <option value="TUBULAR">TUBULAR</option>
                    <option value="ROD">ROD</option>
                    <option value="END_BURNER">END_BURNER</option>
                  </select>
                </label>
                <div className="grid">
                  <NumberField
                    label="Outer dia"
                    unit="m"
                    value={g.outer_diameter}
                    onChange={(v) =>
                      updateStage(i, (st) => ({
                        ...st,
                        motor: {
                          ...st.motor,
                          grain: { ...st.motor.grain, outer_diameter: v },
                        },
                      }))
                    }
                  />
                  <NumberField
                    label="Core dia"
                    unit="m"
                    value={g.core_diameter}
                    onChange={(v) =>
                      updateStage(i, (st) => ({
                        ...st,
                        motor: {
                          ...st.motor,
                          grain: { ...st.motor.grain, core_diameter: v },
                        },
                      }))
                    }
                  />
                  <NumberField
                    label="Segment len"
                    unit="m"
                    value={g.segment_length}
                    onChange={(v) =>
                      updateStage(i, (st) => ({
                        ...st,
                        motor: {
                          ...st.motor,
                          grain: { ...st.motor.grain, segment_length: v },
                        },
                      }))
                    }
                  />
                  <NumberField
                    label="Segments"
                    step={1}
                    min={1}
                    value={g.segments}
                    onChange={(v) =>
                      updateStage(i, (st) => ({
                        ...st,
                        motor: {
                          ...st.motor,
                          grain: { ...st.motor.grain, segments: Math.round(v) },
                        },
                      }))
                    }
                  />
                  <NumberField
                    label="Throat dia"
                    unit="m"
                    value={n.throat_diameter}
                    onChange={(v) =>
                      updateStage(i, (st) => ({
                        ...st,
                        motor: {
                          ...st.motor,
                          nozzle: { ...st.motor.nozzle, throat_diameter: v },
                        },
                      }))
                    }
                  />
                  <NumberField
                    label="Ignition delay"
                    unit="s"
                    step={0.5}
                    min={0}
                    value={stage.ignition_delay}
                    onChange={(v) =>
                      updateStage(i, (st) => ({
                        ...st,
                        ignition_delay: Math.max(0, v),
                      }))
                    }
                  />
                  <NumberField
                    label="Struct. mass"
                    unit="kg"
                    step={0.5}
                    min={0}
                    value={stage.structural_mass}
                    onChange={(v) =>
                      updateStage(i, (st) => ({
                        ...st,
                        structural_mass: Math.max(0, v),
                      }))
                    }
                  />
                </div>
              </div>
            );
          })}

          <div className="export-row">
            <button onClick={addStage} disabled={stages.length >= 5}>
              + Add stage
            </button>
          </div>
          <button className="run" onClick={run} disabled={busy}>
            {busy ? "Simulating…" : "Run stack"}
          </button>
          {error && <p className="error">{error}</p>}

          <hr style={{ margin: "1.2rem 0", opacity: 0.2 }} />
          <h3 style={{ margin: "0 0 0.6rem" }}>Flight parameters</h3>
          <p className="muted" style={{ marginBottom: "0.8rem" }}>
            Payload carried by the top stage; launch conditions for the full
            stack. Spent-stage inert mass is jettisoned at each burnout.
          </p>
          <div className="grid">
            <NumberField
              label="Payload mass"
              unit="kg"
              step={1}
              min={1}
              value={payload.dry_mass}
              onChange={(v) => setPayload((p) => ({ ...p, dry_mass: v }))}
            />
            <NumberField
              label="Payload dia"
              unit="m"
              value={payload.diameter}
              onChange={(v) => setPayload((p) => ({ ...p, diameter: v }))}
            />
            <NumberField
              label="Payload Cd0"
              step={0.01}
              value={payload.cd0}
              onChange={(v) => setPayload((p) => ({ ...p, cd0: v }))}
            />
            <NumberField
              label="Launch speed"
              unit="m/s"
              step={5}
              min={0}
              value={launchSpeed}
              onChange={setLaunchSpeed}
            />
            <NumberField
              label="Elevation"
              unit="°"
              step={1}
              min={0}
              max={90}
              value={elevationDeg}
              onChange={setElevationDeg}
            />
            <NumberField
              label="Azimuth"
              unit="°"
              step={5}
              value={azimuthDeg}
              onChange={setAzimuthDeg}
            />
          </div>
          <label className="field" style={{ marginTop: "0.4rem" }}>
            <input
              type="checkbox"
              checked={dropLast}
              onChange={(e) => setDropLast(e.target.checked)}
              style={{ marginRight: "0.4rem" }}
            />
            Drop last stage at burnout
          </label>
          <button
            className="run"
            style={{ marginTop: "0.8rem" }}
            onClick={fly}
            disabled={flyBusy}
          >
            {flyBusy ? "Flying…" : "Fly stack"}
          </button>
          {flyError && <p className="error">{flyError}</p>}
        </section>

        <section className="results">
          {s && (
            <>
              <div className="stats">
                <Stat label="Total impulse" value={`${s.total_impulse.toFixed(0)} N·s`} />
                <Stat label="Class" value={s.impulse_class} />
                <Stat label="Peak thrust" value={`${s.peak_thrust.toFixed(0)} N`} />
                <Stat label="Stack burn" value={`${s.burn_time.toFixed(1)} s`} />
                <Stat label="Stages" value={String(s.stage_count)} />
                <Stat label="Prop mass" value={`${s.propellant_mass_total.toFixed(1)} kg`} />
              </div>

              <LineChart
                xlabel="Time (s)"
                ylabel="Thrust (N)"
                series={[
                  {
                    label: "Stack thrust",
                    color: "#6366f1",
                    x: result!.time,
                    y: result!.thrust,
                  },
                ]}
              />

              <table className="shots">
                <thead>
                  <tr>
                    <th>Stage</th>
                    <th>Ignite</th>
                    <th>Burn</th>
                    <th>Impulse</th>
                    <th>Class</th>
                  </tr>
                </thead>
                <tbody>
                  {result!.stages.map((st) => (
                    <tr key={st.index}>
                      <td>{st.index + 1}</td>
                      <td>{st.start_time.toFixed(2)} s</td>
                      <td>{st.burn_time.toFixed(2)} s</td>
                      <td>{st.total_impulse.toFixed(0)} N·s</td>
                      <td>{st.impulse_class}</td>
                    </tr>
                  ))}
                </tbody>
              </table>

              <div className="export-row">
                <button onClick={exportCsv}>Stack thrust CSV</button>
              </div>
            </>
          )}

          {fs && flightResult && (
            <>
              <h3 style={{ margin: "1.4rem 0 0.6rem" }}>Flight result</h3>
              <div className="stats">
                <Stat label="Apogee" value={`${(fs.apogee / 1000).toFixed(2)} km`} />
                <Stat label="Max speed" value={`${fs.max_speed.toFixed(0)} m/s`} />
                <Stat label="Max Mach" value={fs.max_mach.toFixed(2)} />
                <Stat label="Range" value={`${(fs.range / 1000).toFixed(2)} km`} />
                <Stat label="Flight time" value={`${fs.flight_time.toFixed(1)} s`} />
                <Stat
                  label="Initial mass"
                  value={`${flightResult.initial_mass.toFixed(1)} kg`}
                />
                <Stat
                  label="Total impulse"
                  value={`${flightResult.total_impulse.toFixed(0)} N·s`}
                />
              </div>

              <TrajectoryPlot
                paths={[
                  {
                    label: "Staged flight",
                    color: "#10b981",
                    ground: groundRange,
                    alt: flightResult.altitude,
                  },
                ]}
                markers={sepMarkers}
              />

              <LineChart
                xlabel="Time (s)"
                ylabel="Speed (m/s)"
                series={[
                  {
                    label: "Speed",
                    color: "#10b981",
                    x: flightResult.time,
                    y: flightResult.speed,
                  },
                ]}
              />

              <LineChart
                xlabel="Time (s)"
                ylabel="Mass (kg)"
                series={[
                  {
                    label: "Total mass",
                    color: "#f59e0b",
                    x: flightResult.time,
                    y: flightResult.mass,
                  },
                ]}
              />

              {flightResult.separations.length > 0 && (
                <>
                  <h4 style={{ margin: "1rem 0 0.4rem" }}>Stage separations</h4>
                  <table className="shots">
                    <thead>
                      <tr>
                        <th>Event</th>
                        <th>Time</th>
                        <th>Altitude</th>
                        <th>Mass after</th>
                      </tr>
                    </thead>
                    <tbody>
                      {flightResult.separations.map((ev, i) => (
                        <tr key={i}>
                          <td>Stage {i + 1} jettison</td>
                          <td>{ev.time.toFixed(2)} s</td>
                          <td>{(ev.altitude / 1000).toFixed(2)} km</td>
                          <td>{ev.mass_after.toFixed(1)} kg</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </>
              )}

              <div className="export-row">
                <button onClick={exportFlightCsv}>Flight CSV</button>
              </div>
            </>
          )}

          {!s && !fs && (
            <p className="muted">Define the stages and run the stack.</p>
          )}
        </section>
      </div>
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="stat">
      <span className="stat-value">{value}</span>
      <span className="stat-label">{label}</span>
    </div>
  );
}
