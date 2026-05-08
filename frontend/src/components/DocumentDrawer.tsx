import { useEffect, useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import {
  X, FileText, AlertTriangle, Trash2, Loader2,
  ChevronDown, ChevronRight, CheckCircle2,
  Utensils, Car, BedDouble, Monitor, Package, RefreshCw,
  type LucideIcon,
} from "lucide-react";
import { deleteDocument, revalidateDocument, updateDocumentStatus, fileUrl } from "../api";
import { t } from "../theme";
import { StatusBadge } from "./StatusBadge";
import type { Extraction } from "../types";

interface Props {
  doc: Extraction;
  onClose: () => void;
  onDocChange: (doc: Extraction) => void;
}

// ── Category config ───────────────────────────────────────────────────────
const CATEGORY: Record<string, {
  label: string;
  Icon: LucideIcon;
  bg: string;
  text: string;
  ring: string;
}> = {
  meals:         { label: "Meals",         Icon: Utensils,   bg: "bg-orange-50",  text: "text-orange-700", ring: "ring-orange-200" },
  transport:     { label: "Transport",     Icon: Car,        bg: "bg-sky-50",     text: "text-sky-700",    ring: "ring-sky-200"    },
  accommodation: { label: "Accommodation", Icon: BedDouble,  bg: "bg-violet-50",  text: "text-violet-700", ring: "ring-violet-200" },
  equipment:     { label: "Equipment",     Icon: Monitor,    bg: "bg-slate-50",   text: "text-slate-700",  ring: "ring-slate-200"  },
  other:         { label: "Other",         Icon: Package,    bg: "bg-gray-50",    text: "text-gray-600",   ring: "ring-gray-200"   },
};

function fmtDate(iso: string) {
  return new Date(iso).toLocaleDateString("en-US", {
    year: "numeric", month: "long", day: "numeric",
  });
}

function fmtCurrency(n: number, currency: string) {
  return new Intl.NumberFormat("en-US", { style: "currency", currency: currency || "USD" }).format(n);
}

function humanize(key: string) {
  return key.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

interface FilePreview { url: string; type: string }

export function DocumentDrawer({ doc, onClose, onDocChange }: Props) {
  const [preview, setPreview]         = useState<FilePreview | null>(null);
  const [lineItemsOpen, setLineItemsOpen] = useState(false);
  const queryClient = useQueryClient();

  // ── File preview ────────────────────────────────────────────────────
  useEffect(() => {
    let url: string | null = null;
    fetch(fileUrl(doc.schema_key, doc.id))
      .then((res) => {
        if (!res.ok) return null;
        const type = res.headers.get("content-type") ?? "";
        return res.blob().then((b) => ({ blob: b, type }));
      })
      .then((r) => {
        if (!r) return;
        url = URL.createObjectURL(r.blob);
        setPreview({ url, type: r.type });
      })
      .catch(() => {});
    return () => { if (url) URL.revokeObjectURL(url); };
  }, [doc.id, doc.schema_key]);

  // ── Escape ──────────────────────────────────────────────────────────
  useEffect(() => {
    const fn = (e: KeyboardEvent) => { if (e.key === "Escape") onClose(); };
    window.addEventListener("keydown", fn);
    return () => window.removeEventListener("keydown", fn);
  }, [onClose]);

  // ── Delete ──────────────────────────────────────────────────────────
  const deleteMutation = useMutation({
    mutationFn: () => deleteDocument(doc.schema_key, doc.id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["documents", doc.schema_key] });
      onClose();
    },
  });

  // ── Status toggle ────────────────────────────────────────────────────
  const statusMutation = useMutation({
    mutationFn: (status: "accepted" | "needs_review") =>
      updateDocumentStatus(doc.schema_key, doc.id, status),
    onSuccess: (updated) => {
      queryClient.invalidateQueries({ queryKey: ["documents", doc.schema_key] });
      onDocChange(updated);
    },
  });

  // ── Recompute ────────────────────────────────────────────────────────
  const recomputeMutation = useMutation({
    mutationFn: () => revalidateDocument(doc.schema_key, doc.id),
    onSuccess: (updated) => {
      queryClient.invalidateQueries({ queryKey: ["documents", doc.schema_key] });
      onDocChange(updated);
    },
  });

  const { data, enrichments } = doc;
  const category = enrichments?.category;
  const cat = category ? CATEGORY[category] ?? CATEGORY.other : null;
  const currentStatus = enrichments?.status;
  const isImage = preview?.type.startsWith("image/");
  const isPdf   = preview?.type === "application/pdf";
  const hasLineItems = (data.line_items?.length ?? 0) > 0;

  return (
    <div className="fixed inset-0 z-50 flex justify-end">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/30 backdrop-blur-[2px]"
        onClick={onClose}
      />

      {/* Drawer — 80vw, data left / doc right */}
      <aside
        className="relative z-10 flex bg-white shadow-2xl animate-slide-in overflow-hidden"
        style={{ width: "min(80vw, 1200px)" }}
      >

        {/* ── LEFT — data panel ─────────────────────────────────────── */}
        <div className="w-[380px] shrink-0 flex flex-col border-r border-gray-100 overflow-hidden">

          {/* Header */}
          <div className="flex items-center gap-3 px-5 py-4 border-b border-gray-100 shrink-0">
            <FileText size={14} className="text-gray-300 shrink-0" />
            <div className="flex-1 min-w-0">
              <p className="text-sm font-semibold text-gray-900 truncate">
                {doc.file_name ?? "Document"}
              </p>
              <p className="text-xs text-gray-400 mt-0.5">{fmtDate(doc.created_at)}</p>
            </div>
            <button
              onClick={() => deleteMutation.mutate()}
              disabled={deleteMutation.isPending}
              className={`${t.btnDanger} disabled:opacity-40`}
              title="Delete receipt"
            >
              {deleteMutation.isPending
                ? <Loader2 size={14} className="animate-spin" />
                : <Trash2 size={14} />
              }
            </button>
            <button onClick={onClose} className="text-gray-300 hover:text-gray-600 transition-colors">
              <X size={18} />
            </button>
          </div>

          {/* AI hero — category + status + violations */}
          <div className={`shrink-0 px-5 py-5 border-b border-gray-100 space-y-3 ${cat ? cat.bg : "bg-gray-50"}`}>

            {/* Category badge (large) */}
            {cat ? (
              <div className={`inline-flex items-center gap-2.5 px-4 py-2 rounded-2xl ring-1 ${cat.bg} ${cat.text} ${cat.ring}`}>
                <cat.Icon size={16} />
                <span className="text-sm font-bold tracking-wide">{cat.label}</span>
              </div>
            ) : (
              <div className="inline-flex items-center gap-2 px-4 py-2 rounded-2xl bg-gray-100 text-gray-400 ring-1 ring-gray-200">
                <Package size={15} />
                <span className="text-sm font-semibold">Uncategorized</span>
              </div>
            )}

            {/* Status + actions */}
            <div className="flex items-center justify-between">
              <StatusBadge status={currentStatus} size="md" />

              <div className="flex items-center gap-1">
                <button
                  onClick={() => recomputeMutation.mutate()}
                  disabled={recomputeMutation.isPending}
                  className="text-xs font-semibold text-gray-400 hover:text-gray-600 hover:bg-gray-100 px-2.5 py-1.5 rounded-lg transition-colors disabled:opacity-40"
                  title="Re-run AI validation"
                >
                  {recomputeMutation.isPending
                    ? <Loader2 size={12} className="animate-spin" />
                    : <RefreshCw size={12} />
                  }
                </button>

                {currentStatus === "accepted" ? (
                  <button
                    onClick={() => statusMutation.mutate("needs_review")}
                    disabled={statusMutation.isPending}
                    className="text-xs font-semibold text-amber-600 hover:text-amber-700 hover:bg-amber-50 px-2.5 py-1.5 rounded-lg transition-colors disabled:opacity-40"
                  >
                    {statusMutation.isPending ? <Loader2 size={12} className="animate-spin inline" /> : "Flag for review"}
                  </button>
                ) : (
                  <button
                    onClick={() => statusMutation.mutate("accepted")}
                    disabled={statusMutation.isPending}
                    className="text-xs font-semibold text-emerald-600 hover:text-emerald-700 hover:bg-emerald-50 px-2.5 py-1.5 rounded-lg transition-colors disabled:opacity-40"
                  >
                    {statusMutation.isPending ? <Loader2 size={12} className="animate-spin inline" /> : "Mark accepted"}
                  </button>
                )}
              </div>
            </div>

            {/* Violations */}
            {enrichments?.violations && enrichments.violations.length > 0 && (
              <div className="rounded-xl bg-amber-50 border border-amber-200 p-3">
                <div className="flex items-center gap-1.5 text-amber-700 text-xs font-bold mb-1.5">
                  <AlertTriangle size={12} />
                  Policy Violations
                </div>
                <ul className="space-y-1">
                  {enrichments.violations.map((v, i) => (
                    <li key={i} className="text-xs text-amber-700 leading-snug">• {v}</li>
                  ))}
                </ul>
              </div>
            )}

            {/* Compliant confirmation */}
            {enrichments?.is_compliant && (!enrichments.violations || enrichments.violations.length === 0) && (
              <div className="flex items-center gap-1.5 text-emerald-600 text-xs font-semibold">
                <CheckCircle2 size={13} />
                All policy rules satisfied
              </div>
            )}
          </div>

          {/* Scrollable fields */}
          <div className="flex-1 overflow-y-auto px-5 py-5 space-y-6">

            {/* Key numbers */}
            <div className="space-y-4">
              <div>
                <p className={t.fieldLabel}>Merchant</p>
                <p className="text-xl font-bold text-gray-900 mt-0.5">{data.merchant_name ?? "—"}</p>
              </div>
              <div>
                <p className={t.fieldLabel}>Total</p>
                <p className="text-2xl font-bold text-gray-900 tabular-nums mt-0.5">
                  {fmtCurrency(data.total_amount, data.currency)}
                </p>
              </div>
            </div>

            {/* Line items (collapsible) */}
            {hasLineItems && (
              <div>
                <button
                  onClick={() => setLineItemsOpen((o) => !o)}
                  className="flex items-center gap-1.5 text-xs font-bold text-gray-400 uppercase tracking-widest hover:text-gray-600 transition-colors group w-full"
                >
                  {lineItemsOpen
                    ? <ChevronDown size={12} />
                    : <ChevronRight size={12} />
                  }
                  Line Items ({data.line_items.length})
                </button>
                {lineItemsOpen && (
                  <div className="mt-3 space-y-2 pl-1">
                    {data.line_items.map((item, i) => (
                      <div key={i} className="flex items-baseline justify-between gap-3 text-sm">
                        <span className="text-gray-600 truncate">
                          {item.quantity && item.quantity !== 1 ? `${item.quantity}× ` : ""}
                          {item.description}
                        </span>
                        <span className="font-semibold text-gray-900 tabular-nums shrink-0">
                          {fmtCurrency(item.total, data.currency)}
                        </span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}

            {/* Secondary details */}
            <div className="space-y-3 pt-2 border-t border-gray-100">
              <Field label="Date"    value={data.date ?? "—"} />
              <Field label="Payment" value={data.payment_method ? humanize(data.payment_method) : "—"} />
            </div>
          </div>
        </div>

        {/* ── RIGHT — document preview ───────────────────────────────── */}
        <div className="flex-1 bg-gray-100 overflow-hidden flex items-center justify-center">
          {isImage && preview && (
            <img
              src={preview.url}
              alt={doc.file_name ?? "receipt"}
              className="max-w-full max-h-full object-contain p-6"
            />
          )}
          {isPdf && preview && (
            <iframe src={preview.url} className="w-full h-full border-0" title="Document preview" />
          )}
          {!preview && (
            <div className="flex flex-col items-center gap-3 text-gray-400">
              <FileText size={56} strokeWidth={1} />
              <p className="text-sm font-medium">No preview</p>
            </div>
          )}
        </div>
      </aside>
    </div>
  );
}

function Field({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-baseline justify-between gap-4">
      <dt className={t.fieldLabel}>{label}</dt>
      <dd className={`${t.fieldValue} text-right`}>{value}</dd>
    </div>
  );
}
