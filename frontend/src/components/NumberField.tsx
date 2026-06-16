interface NumberFieldProps {
  label: string;
  value: number;
  onChange: (v: number) => void;
  step?: number;
  min?: number;
  max?: number;
  unit?: string;
}

/** Labelled numeric input used throughout the parameter forms. */
export default function NumberField({
  label,
  value,
  onChange,
  step = 0.01,
  min,
  max,
  unit,
}: NumberFieldProps) {
  return (
    <label className="field">
      <span className="field-label">
        {label}
        {unit ? ` (${unit})` : ""}
      </span>
      <input
        type="number"
        value={value}
        step={step}
        min={min}
        max={max}
        onChange={(e) => {
          const v = parseFloat(e.target.value);
          if (!Number.isNaN(v)) onChange(v);
        }}
      />
    </label>
  );
}
