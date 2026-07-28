"use client";

export default function Sparkline({
  values,
  width = 560,
  height = 120,
}: {
  values: number[];
  width?: number;
  height?: number;
}) {
  if (values.length === 0) return null;

  const pad = 12;
  const min = Math.min(...values, 0);
  const max = Math.max(...values, 100);
  const span = max - min || 1;
  const stepX =
    values.length > 1 ? (width - pad * 2) / (values.length - 1) : 0;

  const points = values.map((v, i) => {
    const x = pad + i * stepX;
    const y = height - pad - ((v - min) / span) * (height - pad * 2);
    return [x, y] as const;
  });
  const polyline = points.map(([x, y]) => `${x},${y}`).join(" ");
  const area = `${pad},${height - pad} ${polyline} ${
    points[points.length - 1][0]
  },${height - pad}`;

  return (
    <svg
      viewBox={`0 0 ${width} ${height}`}
      className="w-full"
      role="img"
      aria-label="Score trend over time"
    >
      <polygon points={area} fill="#0d9488" opacity={0.08} />
      <polyline
        points={polyline}
        fill="none"
        stroke="#0d9488"
        strokeWidth={3}
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      {points.map(([x, y], i) => (
        <circle
          key={i}
          cx={x}
          cy={y}
          r={i === points.length - 1 ? 5 : 3.5}
          fill={i === points.length - 1 ? "#d97706" : "#0d9488"}
          stroke="#ffffff"
          strokeWidth={1.5}
        />
      ))}
    </svg>
  );
}
