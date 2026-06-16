import { useState } from "react";
import {
  downloadExport,
  simulateMissile,
  type MissileRequest,
  type TrajectoryResult,
} from "../api";
import { defaultMissile } from "../defaults";
import LineChart from "../components/LineChart";
import TrajectoryPlot from "../components/TrajectoryPlot";
import NumberField from "../components/NumberField";

export default function MissilePage() {
  const [req, setReq] = useState<MissileRequest>(structuredClone(defaultMissile));
  const [result, setResult] = useState<TrajectoryResult | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const a = req.airframe;
  const g = req.motor.grain;

  function patch(part: Partial<MissileRequest>) {
    setReq((r) => ({ ...r, ...part }));
  }

  async function run() {
    setBusy(true);
    setError(null);
    try {
      setResult(await simulateMissile(req));
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  }

  const ground = result?.position.map((pp) => Math.hypot(pp[0], pp[1])) ?? [];
  const alt = result?.altitude ?? [];
  const s = result?.summary;

  const airframeReq = {
    airframe: a,
    body_length: 2.5,
    nose_length: 0.6,
    fin_count: 4,
    fin_span: 0.12,
    fin_root: 0.3,
  };

  return (
    <div className="page">
      <h2>Missile flight trajectory</h2>
      <p className="muted">
        3-DOF point-mass flight (RK4) with ISA atmosphere, Mach-dependent drag
        and the motor thrust curve driving boost. No guidance.
      </p>

      <div className="layout">
        <section className="params">
          <h3>Airframe</h3>
          <div className="grid">
            <NumberField label="Body dia" unit="m" value={a.diameter}
              onChange={(v) => patch({ airframe: { ...a, diameter: v } })} />
            <NumberField label="Cd0" value={a.cd0}
              onChange={(v) => patch({ airframe: { ...a, cd0: v } })} />
            <NumberField label="Dry mass" unit="kg" step={1} value={a.dry_mass}
              onChange={(v) => patch({ airframe: { ...a, dry_mass: v } })} />
          </div>

          <h3>Launch</h3>
          <div className="grid">
            <NumberField label="Rail speed" unit="m/s" step={1} value={req.launch_speed}
              onChange={(v) => patch({ launch_speed: v })} />
            <NumberField label="Elevation" unit="°" step={1} min={0} max={90} value={req.elevation_deg}
              onChange={(v) => patch({ elevation_deg: v })} />
            <NumberField label="Azimuth" unit="°" step={1} value={req.azimuth_deg}
              onChange={(v) => patch({ azimuth_deg: v })} />
          </div>

          <h3>Motor grain</h3>
          <div className="grid">
            <NumberField label="Outer dia" unit="m" value={g.outer_diameter}
              onChange={(v) => patch({ motor: { ...req.motor, grain: { ...g, outer_diameter: v } } })} />
            <NumberField label="Core dia" unit="m" value={g.core_diameter}
              onChange={(v) => patch({ motor: { ...req.motor, grain: { ...g, core_diameter: v } } })} />
            <NumberField label="Segment len" unit="m" value={g.segment_length}
              onChange={(v) => patch({ motor: { ...req.motor, grain: { ...g, segment_length: v } } })} />
            <NumberField label="Segments" step={1} min={1} value={g.segments}
              onChange={(v) => patch({ motor: { ...req.motor, grain: { ...g, segments: Math.round(v) } } })} />
          </div>

          <button className="run" onClick={run} disabled={busy}>
            {busy ? "Simulating…" : "Run trajectory"}
          </button>
          {error && <p className="error">{error}</p>}
        </section>

        <section className="results">
          {s && (
            <>
              <div className="stats">
                <Stat label="Apogee" value={`${(s.apogee / 1000).toFixed(2)} km`} />
                <Stat label="Max speed" value={`${s.max_speed.toFixed(0)} m/s`} />
                <Stat label="Max Mach" value={s.max_mach.toFixed(2)} />
                <Stat label="Range" value={`${(s.range / 1000).toFixed(2)} km`} />
                <Stat label="Flight time" value={`${s.flight_time.toFixed(1)} s`} />
              </div>

              <TrajectoryPlot paths={[{ label: "Missile", color: "#6366f1", ground, alt }]} />
              <LineChart
                xlabel="Time (s)"
                ylabel="Speed (m/s)"
                series={[{ label: "Speed", color: "#0891b2", x: result!.time, y: result!.speed }]}
              />

              <h3>Export</h3>
              <div className="export-row">
                <button onClick={() => downloadExport("/export/cad/airframe.stl", airframeReq, "airframe.stl")}>
                  Airframe STL
                </button>
                <button onClick={() => downloadExport("/export/cad/airframe.scad", airframeReq, "airframe.scad")}>
                  Airframe OpenSCAD
                </button>
                <button onClick={() => downloadExport("/export/simulink/trajectory.csv", req, "trajectory.csv")}>
                  Trajectory CSV
                </button>
              </div>
            </>
          )}
          {!s && <p className="muted">Run the simulation to see the trajectory.</p>}
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
