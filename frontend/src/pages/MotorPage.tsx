import { useState } from "react";
import {
  downloadExport,
  simulateMotor,
  type MotorRequest,
  type MotorResult,
} from "../api";
import { APCP, KNSB, defaultMotor } from "../defaults";
import LineChart from "../components/LineChart";
import NumberField from "../components/NumberField";

export default function MotorPage() {
  const [req, setReq] = useState<MotorRequest>(structuredClone(defaultMotor));
  const [result, setResult] = useState<MotorResult | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const p = req.propellant;
  const g = req.grain;
  const n = req.nozzle;

  function patch(part: Partial<MotorRequest>) {
    setReq((r) => ({ ...r, ...part }));
  }

  async function run() {
    setBusy(true);
    setError(null);
    try {
      setResult(await simulateMotor(req));
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  }

  const s = result?.summary;

  return (
    <div className="page">
      <h2>Solid rocket motor — internal ballistics</h2>
      <p className="muted">
        Quasi-steady chamber-pressure model: r = a·Pcⁿ, choked nozzle flow,
        thrust coefficient with altitude pressure correction.
      </p>

      <div className="layout">
        <section className="params">
          <h3>Propellant</h3>
          <div className="preset-row">
            <button onClick={() => patch({ propellant: { ...KNSB } })}>KNSB</button>
            <button onClick={() => patch({ propellant: { ...APCP } })}>APCP</button>
          </div>
          <div className="grid">
            <NumberField label="Density" unit="kg/m³" step={1} value={p.density}
              onChange={(v) => patch({ propellant: { ...p, density: v } })} />
            <NumberField label="Burn coeff a" unit="mm/s@MPa" value={p.a}
              onChange={(v) => patch({ propellant: { ...p, a: v } })} />
            <NumberField label="Burn exp n" value={p.n}
              onChange={(v) => patch({ propellant: { ...p, n: v } })} />
            <NumberField label="γ" value={p.gamma}
              onChange={(v) => patch({ propellant: { ...p, gamma: v } })} />
            <NumberField label="Flame temp" unit="K" step={10} value={p.t_flame}
              onChange={(v) => patch({ propellant: { ...p, t_flame: v } })} />
            <NumberField label="Molar mass" unit="kg/mol" step={0.001} value={p.molar_mass}
              onChange={(v) => patch({ propellant: { ...p, molar_mass: v } })} />
          </div>

          <h3>Grain (BATES)</h3>
          <div className="grid">
            <NumberField label="Outer dia" unit="m" value={g.outer_diameter}
              onChange={(v) => patch({ grain: { ...g, outer_diameter: v } })} />
            <NumberField label="Core dia" unit="m" value={g.core_diameter}
              onChange={(v) => patch({ grain: { ...g, core_diameter: v } })} />
            <NumberField label="Segment len" unit="m" value={g.segment_length}
              onChange={(v) => patch({ grain: { ...g, segment_length: v } })} />
            <NumberField label="Segments" step={1} min={1} value={g.segments}
              onChange={(v) => patch({ grain: { ...g, segments: Math.round(v) } })} />
          </div>

          <h3>Nozzle</h3>
          <div className="grid">
            <NumberField label="Throat dia" unit="m" value={n.throat_diameter}
              onChange={(v) => patch({ nozzle: { ...n, throat_diameter: v } })} />
            <NumberField label="Expansion ε" value={n.expansion_ratio}
              onChange={(v) => patch({ nozzle: { ...n, expansion_ratio: v } })} />
            <NumberField label="Altitude" unit="m" step={100} value={req.altitude}
              onChange={(v) => patch({ altitude: v })} />
          </div>

          <button className="run" onClick={run} disabled={busy}>
            {busy ? "Simulating…" : "Run motor simulation"}
          </button>
          {error && <p className="error">{error}</p>}
        </section>

        <section className="results">
          {s && (
            <>
              <div className="stats">
                <Stat label="Total impulse" value={`${s.total_impulse.toFixed(0)} N·s`} />
                <Stat label="Class" value={s.impulse_class} />
                <Stat label="Peak thrust" value={`${s.peak_thrust.toFixed(0)} N`} />
                <Stat label="Avg thrust" value={`${s.average_thrust.toFixed(0)} N`} />
                <Stat label="Burn time" value={`${s.burn_time.toFixed(2)} s`} />
                <Stat label="Isp" value={`${s.specific_impulse.toFixed(0)} s`} />
                <Stat label="Peak pressure" value={`${(s.peak_pressure / 1e6).toFixed(2)} MPa`} />
                <Stat label="Prop mass" value={`${s.propellant_mass_initial.toFixed(2)} kg`} />
              </div>

              <LineChart
                xlabel="Time (s)"
                ylabel="Thrust (N)"
                series={[{ label: "Thrust", color: "#6366f1", x: result!.time, y: result!.thrust }]}
              />
              <LineChart
                xlabel="Time (s)"
                ylabel="Chamber pressure (MPa)"
                series={[{
                  label: "Pc",
                  color: "#dc2626",
                  x: result!.time,
                  y: result!.chamber_pressure.map((v) => v / 1e6),
                }]}
              />

              <h3>Export</h3>
              <div className="export-row">
                <button onClick={() => downloadExport("/export/cad/grain.stl", req, "grain.stl")}>
                  Grain STL
                </button>
                <button onClick={() => downloadExport("/export/cad/nozzle.stl", req, "nozzle.stl")}>
                  Nozzle STL
                </button>
                <button onClick={() => downloadExport("/export/cad/grain.scad", req, "grain.scad")}>
                  Grain OpenSCAD
                </button>
                <button onClick={() => downloadExport("/export/cad/nozzle.scad", req, "nozzle.scad")}>
                  Nozzle OpenSCAD
                </button>
                <button onClick={() => downloadExport("/export/simulink/thrust_curve.csv", req, "thrust_curve.csv")}>
                  Thrust CSV
                </button>
                <button onClick={() => downloadExport("/export/simulink/motor.eng", req, "motor.eng")}>
                  RASP .eng
                </button>
              </div>
            </>
          )}
          {!s && <p className="muted">Run the simulation to see the thrust curve and exports.</p>}
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
