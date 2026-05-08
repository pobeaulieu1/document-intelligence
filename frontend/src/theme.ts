/**
 * theme.ts — reusable Tailwind class strings.
 *
 * Edit here to change the look of every button, badge, or section in one place.
 * Import: import { t } from "../theme"
 */
export const t = {
  // ── Buttons ─────────────────────────────────────────────────────────
  btnPrimary:
    "inline-flex items-center gap-2 px-4 py-2.5 bg-brand-600 text-white text-sm font-semibold rounded-xl hover:bg-brand-700 active:scale-[0.98] transition-all shadow-sm",
  btnGhost:
    "inline-flex items-center gap-2 px-3 py-2 text-sm font-medium text-gray-600 hover:bg-gray-100 rounded-lg transition-colors",
  btnDanger:
    "inline-flex items-center gap-2 px-3 py-2 text-sm font-medium text-red-600 hover:bg-red-50 rounded-lg transition-colors",
  btnDangerSolid:
    "inline-flex items-center gap-2 px-3 py-2 text-sm font-semibold text-white bg-red-600 hover:bg-red-700 rounded-lg transition-colors",
  btnOutline:
    "inline-flex items-center gap-2 px-4 py-2.5 text-sm font-medium text-gray-700 bg-white border border-gray-200 rounded-xl hover:bg-gray-50 transition-colors",

  // ── Cards / surfaces ────────────────────────────────────────────────
  card: "bg-white rounded-2xl border border-gray-100 shadow-card overflow-hidden",

  // ── Stat cards ──────────────────────────────────────────────────────
  statCard: "bg-white rounded-2xl border border-gray-100 shadow-card px-5 py-4",
  statLabel: "text-xs font-semibold text-gray-400 uppercase tracking-widest",
  statValue: "text-2xl font-bold text-gray-900 mt-1 tabular-nums",

  // ── Table ───────────────────────────────────────────────────────────
  tableHead:
    "px-5 py-3 text-left text-[11px] font-semibold text-gray-400 uppercase tracking-widest whitespace-nowrap",
  tableCell: "px-5 py-4 text-sm",

  // ── Drawer sections ─────────────────────────────────────────────────
  sectionTitle:
    "text-[10px] font-bold text-gray-400 uppercase tracking-widest mb-3",
  fieldLabel: "text-xs text-gray-400",
  fieldValue: "text-sm font-medium text-gray-900",

  // ── Form ────────────────────────────────────────────────────────────
  modalTitle: "text-lg font-semibold text-gray-900",
} as const;
