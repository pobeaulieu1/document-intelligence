import { useEffect, useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import {
  X, FileText, AlertTriangle, Trash2, Loader2,
  CheckCircle2, Sparkles, RefreshCw,
  Utensils, Car, BedDouble, Monitor, Package,
  type LucideIcon,
} from "lucide-react";
import { deleteDocument, revalidateDocument, fileUrl } from "../api";
import { t } from "../theme";
import { StatusBadge } from "./StatusBadge";
import type { Extraction } from "../types";

interface Props {
  doc: Extraction;
  onClose: () => void;
  onDocChange: (doc: Extraction) => void;
}

const CATEGORY: Record<string, {
  label: string;
  Icon: LucideIcon;
  bg: string;
  text: string;
  ring: string;
}> = {
  meals:         { label: "Meals",         Icon: Utensils,  bg: "bg-orange-50",  text: "text-orange-700", ring: "ring-orange-200"  },
  transport:     { label: "Transport",     Icon: Car,       bg: "bg-sky-50",     text: "text-sky-700",    ring: "ring-sky-200"     },
  accommodation: { label: "Accommodation", Icon: BedDouble, bg: "bg-violet-50",  text: "text-violet-700", ring: "ring-violet-200"  },
  equipment:     { label: "Equipment",     Icon: Monitor,   bg: "bg-slate-50",   text: "text-slate-700",  ring: "ring-slate-200"   },
  other:         { label: "Other",         Icon: Package,   bg: "bg-gray-50",    text: "text-gray-600",   ring: "ring-gray-200"    },
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

function Skeleton({ className }: { className?: string }) {
  return <div className={"animate-pulse bg-gray-100 rounded-lg " + (className ?? "")} />;
}

interface FilePreview { url: string; type: string }

export function DocumentDrawer({ doc, onClose, onDocChange }: Props) {
  const [preview, setPreview] = useState<FilePreview | null>(null);
  const queryClient           = useQueryClient();

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

  useEffect(() => {
    const fn = (e: KeyboardEvent) => { if (e.key === "Escape") onClose(); };
    window.addEventListener("keydown", fn);
    return () => window.removeEventListener("keydown", fn);
  }, [onClose]);

  const deleteMutation = useMutation({
    mutationFn: () => deleteDocument(doc.schema_key, doc.id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["documents", doc.schema_key] });
      onClose();
    },
  });

  const recomputeMutation = useMutation({
    mutationFn: () => revalidateDocument(doc.schema_key, doc.id),
    onSuccess: (updated) => {
      queryClient.invalidateQueries({ queryKey: ["documents", doc.schema_key] });
      onDocChange(updated);
    },
  });

  const { data, enrichments } = doc;
  const category      = enrichments?.category;
  const cat           = category ? CATEGORY[category] ?? CATEGORY.other : null;
  const currentStatus = enrichments?.status;
  const isImage       = preview?.type.startsWith("image/");
  const isPdf         = preview?.type === "application/pdf";
  const loading       = recomputeMutation.isPending;

  return (
    <div className="fixed inset-0 z-50 flex justify-end">
      <div className="absolute inset-0 bg-black/30 backdrop-blur-[2px]" onClick={onClose} />

      <aside
        className="relative z-10 flex bg-white shadow-2xl animate-slide-in overflow-hidden"
        style={{ width: "min(80vw, 1200px)" }}
      >
        <div className="flex-1 bg-gray-100 overflow-hidden flex items-center justify-center">
          {isImage && preview && (
            <img src={preview.url} alt={doc.file_name ?? "receipt"} className="max-w-full max-h-full object-contain p-6" />
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

        <div className="w-[460px] shrink-0 flex flex-col border-l border-gray-100 overflow-hidden">

          <div className="flex items-center gap-3 px-5 py-4 border-b border-gray-100 shrink-0">
            <FileText size={14} className="text-gray-300 shrink-0" />
            <div className="flex-1 min-w-0">
              <p className="text-sm font-semibold text-gray-900 truncate">{doc.file_name ?? "Document"}</p>
              <p className="text-xs text-gray-400 mt-0.5">{fmtDate(doc.created_at)}</p>
            </div>
            <button
              onClick={() => recomputeMutation.mutate()}
              disabled={loading || deleteMutation.isPending}
              className="text-gray-300 hover:text-gray-600 transition-colors disabled:opacity-40"
              title="Re-run AI validation"
            >
              {loading
                ? <Loader2 size={15} className="animate-spin" />
                : <RefreshCw size={15} />}
            </button>
            <button
              onClick={() => deleteMutation.mutate()}
              disabled={deleteMutation.isPending || loading}
              className={t.btnDanger + " disabled:opacity-40"}
              title="Delete receipt"
            >
              {deleteMutation.isPending
                ? <Loader2 size={14} className="animate-spin" />
                : <Trash2 size={14} />}
            </button>
            <button onClick={onClose} className="text-gray-300 hover:text-gray-600 transition-colors">
              <X size={18} />
            </button>
          </div>

          <div className="flex-1 overflow-y-auto">

            <div className="px-5 pt-5 pb-4 border-b border-gray-100">
              <p className={t.sectionTitle + " mb-3"}>Summary</p>
              <div className="rounded-2xl bg-gradient-to-br from-violet-50 via-indigo-50 to-blue-50 border border-indigo-100 p-4">
                {loading ? (
                  <div className="space-y-2">
                    <Skeleton className="h-3.5 w-full" />
                    <Skeleton className="h-3.5 w-4/5" />
                    <Skeleton className="h-3.5 w-2/3" />
                  </div>
                ) : (
                  <div className="flex items-start gap-2.5">
                    <Sparkles size={13} className="text-violet-400 mt-0.5 shrink-0" />
                    <p className="text-sm font-medium text-gray-800 leading-relaxed">
                      {enrichments?.summary
                        ? enrichments.summary
                        : <span className="text-gray-400 italic font-normal">No summary yet — click refresh</span>}
                    </p>
                  </div>
                )}
              </div>
            </div>

            <div className="px-5 pt-5 pb-4 border-b border-gray-100">
              <div className="flex items-center justify-between">
                <p className={t.sectionTitle}>Classification</p>
                {loading ? (
                  <Skeleton className="h-6 w-28" />
                ) : cat ? (
                  <div className={"inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-bold ring-1 " + cat.bg + " " + cat.text + " " + cat.ring}>
                    <cat.Icon size={11} />
                    {cat.label}
                  </div>
                ) : (
                  <div className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-bold ring-1 bg-gray-100 text-gray-400 ring-gray-200">
                    <Package size={11} />
                    Other
                  </div>
                )}
              </div>
            </div>

            <div className="px-5 pt-5 pb-4 border-b border-gray-100 space-y-3">
              <div className="flex items-center justify-between">
                <p className={t.sectionTitle}>Company Policy</p>
                {loading
                  ? <Skeleton className="h-6 w-20" />
                  : <StatusBadge status={currentStatus} size="md" />}
              </div>

              {loading ? (
                <div className="space-y-2">
                  <Skeleton className="h-3.5 w-3/4" />
                  <Skeleton className="h-3.5 w-1/2" />
                </div>
              ) : (
                <>
                  {enrichments?.violations && enrichments.violations.length > 0 && (
                    <div className="rounded-xl bg-amber-50 border border-amber-200 p-3">
                      <div className="flex items-center gap-1.5 text-amber-700 text-xs font-bold mb-1.5">
                        <AlertTriangle size={12} />
                        Violations
                      </div>
                      <ul className="space-y-1">
                        {enrichments.violations.map((v, i) => (
                          <li key={i} className="text-xs text-amber-700 leading-snug">
                            {v}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                  {enrichments?.is_compliant && (!enrichments.violations || enrichments.violations.length === 0) && (
                    <div className="flex items-center gap-1.5 text-emerald-600 text-xs font-semibold">
                      <CheckCircle2 size={13} />
                      All policy rules satisfied
                    </div>
                  )}
                </>
              )}
            </div>

            <div className="px-5 pt-5 pb-4">
              <p className={t.sectionTitle + " mb-1"}>Details</p>
              <div className="divide-y divide-gray-50">
                <Field label="Merchant" value={data.merchant_name ?? "—"} />
                <Field label="Total"    value={fmtCurrency(data.total_amount, data.currency)} />
                <Field label="Date"     value={data.date ?? "—"} />
                <Field label="Payment"  value={data.payment_method ? humanize(data.payment_method) : "—"} />
                <Field label="Uploaded" value={fmtDate(doc.created_at)} />
              </div>
            </div>

          </div>
        </div>
      </aside>
    </div>
  );
}

function Field({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-baseline justify-between gap-4 py-3.5">
      <dt className={t.fieldLabel}>{label}</dt>
      <dd className={t.fieldValue + " text-right"}>{value}</dd>
    </div>
  );
}
