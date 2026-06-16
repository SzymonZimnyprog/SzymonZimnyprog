interface Series {
  label: string;
  color: string;
  x: number[];
  y: number[];
}

interface LineChartProps {
  series: Series[];
  width?: number;
  height?: number;
  xlabel?: string;
  ylabel?: string;
}

/**
 * Minimal dependency-free SVG line chart supporting multiple series sharing a
 * common axis. Auto-scales to the combined data range.
 */
export default function LineChart({
  series,
  width = 560,
  height = 320,
  xlabel = "",
  ylabel = "",
}: LineChartProps) {
  const pad = { left: 64, right: 16, top: 16, bottom: 44 };
  const plotW = width - pad.left - pad.right;
  const plotH = height - pad.top - pad.bottom;

  const allX = series.flatMap((s) => s.x);
  const allY = series.flatMap((s) => s.y);
  if (allX.length === 0) {
    return <p className="muted">No data to plot.</p>;
  }

  const xMin = Math.min(...allX);
  const xMax = Math.max(...allX);
  const yMin = Math.min(0, ...allY);
  const yMax = Math.max(...allY);
  const xSpan = xMax - xMin || 1;
  const ySpan = yMax - yMin || 1;

  const sx = (x: number) => pad.left + ((x - xMin) / xSpan) * plotW;
  const sy = (y: number) => pad.top + plotH - ((y - yMin) / ySpan) * plotH;

  const ticks = 5;
  const xTicks = Array.from({ length: ticks + 1 }, (_, i) => xMin + (xSpan * i) / ticks);
  const yTicks = Array.from({ length: ticks + 1 }, (_, i) => yMin + (ySpan * i) / ticks);

  const fmt = (v: number) => {
    const a = Math.abs(v);
    if (a !== 0 && (a >= 1e4 || a < 1e-2)) return v.toExponential(1);
    return v.toFixed(a >= 100 ? 0 : 2);
  };

  return (
    <svg
      className="chart"
      viewBox={`0 0 ${width} ${height}`}
      role="img"
      aria-label={`${ylabel} versus ${xlabel}`}
    >
      {/* grid + axis ticks */}
      {yTicks.map((t, i) => (
        <g key={`y${i}`}>
          <line x1={pad.left} y1={sy(t)} x2={width - pad.right} y2={sy(t)} className="grid" />
          <text x={pad.left - 8} y={sy(t) + 4} className="tick" textAnchor="end">
            {fmt(t)}
          </text>
        </g>
      ))}
      {xTicks.map((t, i) => (
        <g key={`x${i}`}>
          <text x={sx(t)} y={height - pad.bottom + 18} className="tick" textAnchor="middle">
            {fmt(t)}
          </text>
        </g>
      ))}

      {/* axes */}
      <line x1={pad.left} y1={pad.top} x2={pad.left} y2={pad.top + plotH} className="axis" />
      <line
        x1={pad.left}
        y1={pad.top + plotH}
        x2={width - pad.right}
        y2={pad.top + plotH}
        className="axis"
      />

      {/* series */}
      {series.map((s) => {
        const d = s.x
          .map((x, i) => `${i === 0 ? "M" : "L"}${sx(x).toFixed(1)},${sy(s.y[i]).toFixed(1)}`)
          .join(" ");
        return <path key={s.label} d={d} fill="none" stroke={s.color} strokeWidth={2} />;
      })}

      {/* labels */}
      <text x={width / 2} y={height - 6} className="axis-label" textAnchor="middle">
        {xlabel}
      </text>
      <text
        x={14}
        y={height / 2}
        className="axis-label"
        textAnchor="middle"
        transform={`rotate(-90 14 ${height / 2})`}
      >
        {ylabel}
      </text>

      {/* legend */}
      {series.length > 1 &&
        series.map((s, i) => (
          <g key={`leg${s.label}`} transform={`translate(${pad.left + 8}, ${pad.top + 8 + i * 18})`}>
            <rect width={12} height={12} fill={s.color} />
            <text x={18} y={11} className="tick">
              {s.label}
            </text>
          </g>
        ))}
    </svg>
  );
}
