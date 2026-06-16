interface Path {
  label: string;
  color: string;
  x: number[];
  y: number[];
}

interface PathPlotProps {
  paths: Path[];
  marker?: { x: number; y: number; label: string } | null;
  xlabel?: string;
  ylabel?: string;
  scale?: number; // divide values by this for tick labels (e.g. 1000 -> km)
  unit?: string;
  width?: number;
  height?: number;
}

/**
 * Generic multi-series X/Y plot with auto-scaling that handles negative
 * coordinates (unlike TrajectoryPlot, which assumes non-negative range/alt).
 * Used for the top-down (East/North) plan view of an engagement.
 */
export default function PathPlot({
  paths,
  marker = null,
  xlabel = "",
  ylabel = "",
  scale = 1,
  unit = "",
  width = 560,
  height = 360,
}: PathPlotProps) {
  const pad = { left: 64, right: 16, top: 16, bottom: 44 };
  const plotW = width - pad.left - pad.right;
  const plotH = height - pad.top - pad.bottom;

  const allX = paths.flatMap((p) => p.x).concat(marker ? [marker.x] : []);
  const allY = paths.flatMap((p) => p.y).concat(marker ? [marker.y] : []);
  if (allX.length === 0) return <p className="muted">No data to plot.</p>;

  const xMin = Math.min(...allX);
  const xMax = Math.max(...allX);
  const yMin = Math.min(...allY);
  const yMax = Math.max(...allY);
  const xSpan = xMax - xMin || 1;
  const ySpan = yMax - yMin || 1;

  const sx = (x: number) => pad.left + ((x - xMin) / xSpan) * plotW;
  const sy = (y: number) => pad.top + plotH - ((y - yMin) / ySpan) * plotH;

  const ticks = 5;
  const xTicks = Array.from({ length: ticks + 1 }, (_, i) => xMin + (xSpan * i) / ticks);
  const yTicks = Array.from({ length: ticks + 1 }, (_, i) => yMin + (ySpan * i) / ticks);
  const fmt = (v: number) => (v / scale).toFixed(Math.abs(v / scale) >= 100 ? 0 : 1);

  return (
    <svg className="chart" viewBox={`0 0 ${width} ${height}`} role="img" aria-label={`${ylabel} vs ${xlabel}`}>
      {yTicks.map((t, i) => (
        <g key={`y${i}`}>
          <line x1={pad.left} y1={sy(t)} x2={width - pad.right} y2={sy(t)} className="grid" />
          <text x={pad.left - 8} y={sy(t) + 4} className="tick" textAnchor="end">
            {fmt(t)}
          </text>
        </g>
      ))}
      {xTicks.map((t, i) => (
        <text key={`x${i}`} x={sx(t)} y={height - pad.bottom + 18} className="tick" textAnchor="middle">
          {fmt(t)}
        </text>
      ))}

      <line x1={pad.left} y1={pad.top} x2={pad.left} y2={pad.top + plotH} className="axis" />
      <line x1={pad.left} y1={pad.top + plotH} x2={width - pad.right} y2={pad.top + plotH} className="axis" />

      {paths.map((p) => {
        const d = p.x
          .map((x, i) => `${i === 0 ? "M" : "L"}${sx(x).toFixed(1)},${sy(p.y[i]).toFixed(1)}`)
          .join(" ");
        return <path key={p.label} d={d} fill="none" stroke={p.color} strokeWidth={2} />;
      })}

      {marker && (
        <g>
          <circle cx={sx(marker.x)} cy={sy(marker.y)} r={7} className="marker" />
          <text x={sx(marker.x) + 10} y={sy(marker.y) - 8} className="tick">
            {marker.label}
          </text>
        </g>
      )}

      <text x={width / 2} y={height - 6} className="axis-label" textAnchor="middle">
        {xlabel}
        {unit ? ` (${unit})` : ""}
      </text>
      <text
        x={14}
        y={height / 2}
        className="axis-label"
        textAnchor="middle"
        transform={`rotate(-90 14 ${height / 2})`}
      >
        {ylabel}
        {unit ? ` (${unit})` : ""}
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
