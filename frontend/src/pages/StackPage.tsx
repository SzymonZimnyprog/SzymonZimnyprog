import { useState } from "react";
import {
  simulateMultiStage,
  type GrainType,
  type Stage,
  type StackResult,
} from "../api";
import { APCP, KNSB, defaultStack } from "../defaults";
import LineChart from "../components/LineChart";
import NumberField from "../components/NumberField";

export default function StackPage() {
  const [stages, setStages] = useState<Stage[]>(structuredClone(defaultStack));
  const [result, setResult] = useState<StackResult | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function updateStage(i: number, mut: (s: Stage) => Stage) {
    setStages((prev) => prev.map((s, j) => (j === i ? mut(structuredClone(s)) : s)));
  }

  function addStage() {
    if (stages.length >= 5) return;
    setStages((prev) => [...prev, structuredClone(defaultStack[1])]);
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

  const s = result?.summary;

  return (
    <div className="page">
      <h2>Multi-stage motor stack</h2>
      <p className="muted">
        Sequential stages (boost → sustain): each stage ignites after the
        previous burns out plus its coast delay. The combined thrust profile is
        what a staged interceptor delivers.
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
                    <button onClick={() => updateStage(i, (st) => ({ ...st, motor: { ...st.motor, propellant: { ...KNSB } } }))}>KNSB</button>
                    <button onClick={() => updateStage(i, (st) => ({ ...st, motor: { ...st.motor, propellant: { ...APCP } } }))}>APCP</button>
                    {stages.length > 1 && (
                      <button className="danger" onClick={() => removeStage(i)}>✕</button>
                    )}
                  </div>
                </div>
                <label className="field">
                  <span className="field-label">Grain type</span>
                  <select
                    value={g.grain_type}
                    onChange={(e) =>
                      updateStage(i, (st) => ({ ...st, motor: { ...st.motor, grain: { ...st.motor.grain, grain_type: e.target.value as GrainType } } }))
                    }
                  >
                    <option value="BATES">BATES</option>
                    <option value="TUBULAR">TUBULAR</option>
                    <option value="ROD">ROD</option>
                    <option value="END_BURNER">END_BURNER</option>
                  </select>
                </label>
                <div className="grid">
                  <NumberField label="Outer dia" unit="m" value={g.outer_diameter}
                    onChange={(v) => updateStage(i, (st) => ({ ...st, motor: { ...st.motor, grain: { ...st.motor.grain, outer_diameter: v } } }))} />
                  <NumberField label="Core dia" unit="m" value={g.core_diameter}
                    onChange={(v) => updateStage(i, (st) => ({ ...st, motor: { ...st.motor, grain: { ...st.motor.grain, core_diameter: v } } }))} />
                  <NumberField label="Segment len" unit="m" value={g.segment_length}
                    onChange={(v) => updateStage(i, (st) => ({ ...st, motor: { ...st.motor, grain: { ...st.motor.grain, segment_length: v } } }))} />
                  <NumberField label="Segments" step={1} min={1} value={g.segments}
                    onChange={(v) => updateStage(i, (st) => ({ ...st, motor: { ...st.motor, grain: { ...st.motor.grain, segments: Math.round(v) } } }))} />
                  <NumberField label="Throat dia" unit="m" value={n.throat_diameter}
                    onChange={(v) => updateStage(i, (st) => ({ ...st, motor: { ...st.motor, nozzle: { ...st.motor.nozzle, throat_diameter: v } } }))} />
                  <NumberField label="Ignition delay" unit="s" step={0.5} min={0} value={stage.ignition_delay}
                    onChange={(v) => updateStage(i, (st) => ({ ...st, ignition_delay: Math.max(0, v) }))} />
                </div>
              </div>
            );
          })}

          <div className="export-row">
            <button onClick={addStage} disabled={stages.length >= 5}>+ Add stage</button>
          </div>
          <button className="run" onClick={run} disabled={busy}>
            {busy ? "Simulating…" : "Run stack"}
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
                <Stat label="Stack burn" value={`${s.burn_time.toFixed(1)} s`} />
                <Stat label="Stages" value={String(s.stage_count)} />
                <Stat label="Prop mass" value={`${s.propellant_mass_total.toFixed(1)} kg`} />
              </div>

              <LineChart
                xlabel="Time (s)"
                ylabel="Thrust (N)"
                series={[{ label: "Stack thrust", color: "#6366f1", x: result!.time, y: result!.thrust }]}
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
          {!s && <p className="muted">Define the stages and run the stack.</p>}
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
