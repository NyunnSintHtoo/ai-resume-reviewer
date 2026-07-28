import type { Severity } from "@/lib/types";

const STYLES: Record<Severity, { label: string; className: string }> = {
  good: { label: "Looking good", className: "bg-good-wash text-good" },
  warning: { label: "Could improve", className: "bg-amber-wash text-amber" },
  critical: { label: "Needs attention", className: "bg-crit-wash text-crit" },
};

export default function SeverityChip({ severity }: { severity: Severity }) {
  const s = STYLES[severity] ?? STYLES.warning;
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-bold ${s.className}`}
    >
      <span className="h-1.5 w-1.5 rounded-full bg-current" />
      {s.label}
    </span>
  );
}
