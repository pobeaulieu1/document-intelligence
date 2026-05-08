interface Props {
  status?: string;
  size?: "sm" | "md";
}

const CONFIG: Record<string, { label: string; dot: string; className: string }> = {
  accepted: {
    label: "Accepted",
    dot: "bg-emerald-500",
    className: "bg-emerald-50 text-emerald-700 ring-emerald-500/20",
  },
  needs_review: {
    label: "Review",
    dot: "bg-amber-500",
    className: "bg-amber-50 text-amber-700 ring-amber-500/20",
  },
};

export function StatusBadge({ status, size = "sm" }: Props) {
  const cfg = status ? CONFIG[status] : undefined;
  const base =
    size === "md"
      ? "inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-semibold ring-1 ring-inset"
      : "inline-flex items-center gap-1.5 rounded-full px-2 py-0.5 text-[11px] font-semibold ring-1 ring-inset";

  if (!cfg) {
    return (
      <span className={`${base} bg-gray-50 text-gray-500 ring-gray-400/20`}>
        <span className="h-1.5 w-1.5 rounded-full bg-gray-400" />
        Pending
      </span>
    );
  }

  return (
    <span className={`${base} ${cfg.className}`}>
      <span className={`h-1.5 w-1.5 rounded-full ${cfg.dot}`} />
      {cfg.label}
    </span>
  );
}
