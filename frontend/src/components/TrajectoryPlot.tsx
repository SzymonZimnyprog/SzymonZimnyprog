interface Path {
  label: string;
  color: string;
  ground: number[]; // ground range, m
  alt: number[]; // altitude, m
}

interface TrajectoryPlotProps {
  paths: Path[];
  marker?: { ground: number; alt: number; label: string } | null;
  width?: number;
  height?: number;
}

/**
 * 2D vertical-plane projection (ground range vs altitude) of one or more
 * trajectories, with an optional intercept marker. Dependency-free SVG.
 */
export default function TrajectoryPlot({
  paths,
  marker = null,
  width = 560,
  height = 360,
}: TrajectoryPlotProps) {
  const pad = { left: 64, right: 16, top: 16, bottom: 44 };
  const plotW = width - pad.left - pad.right;
  const plotH = height - pad.top - pad.bottom;

  const allG = paths.flatMap((p) => p.ground);
  const allA = paths.flatMap((p) => p.alt);
  if (allG.length === 0) return <p className="muted">No trajectory to plot.</p>;

  const gMax = Math.max(...allG, marker?.ground ?? 0) || 1;
  const aMax = Math.max(...allA, marker?.alt ?? 0) || 1;

  const sx = (g: number) => pad.left + (g / gMax) * plotW;
  const sy = (a: number) => pad.top + plotH - (a / aMax) * plotH;

  const fmtKm = (m: number) => (m / 1000).toFixed(m >= 1000 ? 1 : 2);
  const ticks = 5;
  const gTicks = Array.from({ length: ticks + 1 }, (_, i) => (gMax * i) / ticks);
  const aTicks = Array.from({ length: ticks + 1 }, (_, i) => (aMax * i) / ticks);

  return (
    <svg className="chart" viewBox={`0 0 ${width} ${height}`} role="img" aria-label="trajectory">
      {aTicks.map((t, i) => (
        <g key={`a${i}`}>
          <line x1={pad.left} y1={sy(t)} x2={width - pad.right} y2={sy(t)} className="grid" />
          <text x={pad.left - 8} y={sy(t) + 4} className="tick" textAnchor="end">
            {fmtKm(t)}
          </text>
        </g>
      ))}
      {gTicks.map((t, i) => (
        <text key={`g${i}`} x={sx(t)} y={height - pad.bottom + 18} className="tick" textAnchor="middle">
          {fmtKm(t)}
        </text>
      ))}

      <line x1={pad.left} y1={pad.top} x2={pad.left} y2={pad.top + plotH} className="axis" />
      <line
        x1={pad.left}
        y1={pad.top + plotH}
        x2={width - pad.right}
        y2={pad.top + plotH}
        className="axis"
      />

      {paths.map((p) => {
        const d = p.ground
          .map((g, i) => `${i === 0 ? "M" : "L"}${sx(g).toFixed(1)},${sy(p.alt[i]).toFixed(1)}`)
          .join(" ");
        return <path key={p.label} d={d} fill="none" stroke={p.color} strokeWidth={2} />;
      })}

      {marker && (
        <g>
          <circle cx={sx(marker.ground)} cy={sy(marker.alt)} r={7} className="marker" />
          <text x={sx(marker.ground) + 10} y={sy(marker.alt) - 8} className="tick">
            {marker.label}
          </text>
        </g>
      )}

      <text x={width / 2} y={height - 6} className="axis-label" textAnchor="middle">
        Ground range (km)
      </text>
      <text
        x={14}
        y={height / 2}
        className="axis-label"
        textAnchor="middle"
        transform={`rotate(-90 14 ${height / 2})`}
      >
        Altitude (km)
      </text>

      {paths.map((p, i) => (
        <g key={`leg${p.label}`} transform={`translate(${pad.left + 8}, ${pad.top + 8 + i * 18})`}>
          <rect width={12} height={12} fill={p.color} />
          <text x={18} y={11} className="tick">
            {p.label}
          </text>
        </g>
      ))}
    </svg>
  );
}
