import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Upload, RefreshCw, ReceiptText, AlertTriangle, DollarSign, Settings } from "lucide-react";
import { listDocuments } from "../api";
import { t } from "../theme";
import { DocumentTable } from "./DocumentTable";
import { DocumentDrawer } from "./DocumentDrawer";
import { UploadModal } from "./UploadModal";
import { SettingsPanel } from "./SettingsPanel";
import type { Extraction } from "../types";

const SCHEMA_KEY = "receipt";

function fmtCurrency(n: number) {
  return new Intl.NumberFormat("en-US", { style: "currency", currency: "USD" }).format(n);
}

export function DocumentsPage() {
  const [selected, setSelected]     = useState<Extraction | null>(null);
  const [showUpload, setShowUpload]  = useState(false);
  const [showSettings, setShowSettings] = useState(false);
  const [newId, setNewId]           = useState<string | undefined>();

  const { data: docs = [], isLoading, isError, refetch } = useQuery({
    queryKey: ["documents", SCHEMA_KEY],
    queryFn: () => listDocuments(SCHEMA_KEY),
  });

  const stats = useMemo(() => ({
    total:      docs.length,
    needReview: docs.filter((d) => d.enrichments?.status === "needs_review").length,
    totalSpend: docs.reduce((s, d) => s + (d.data.total_amount ?? 0), 0),
  }), [docs]);

  function handleUploadSuccess(doc: Extraction) {
    setShowUpload(false);
    setNewId(doc.id);
    setTimeout(() => setNewId(undefined), 2500);
  }

  return (
    <div className="min-h-screen bg-[#f7f8fa]">
      {/* ── Top nav ──────────────────────────────────────────────────── */}
      <header className="bg-white border-b border-gray-100">
        <div className="max-w-7xl mx-auto px-6 h-14 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="w-7 h-7 rounded-lg bg-brand-600 flex items-center justify-center">
              <ReceiptText size={14} className="text-white" />
            </div>
            <span className="text-sm font-semibold text-gray-900">
              Expense Intelligence
            </span>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={() => setShowSettings(true)}
              className={t.btnGhost}
              title="Settings"
            >
              <Settings size={15} />
              Settings
            </button>
            <button
              onClick={() => setShowUpload(true)}
              className={t.btnPrimary}
            >
              <Upload size={14} />
              Upload Receipt
            </button>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-6 py-8 space-y-6">
        {/* ── Stats row ──────────────────────────────────────────────── */}
        {!isLoading && docs.length > 0 && (
          <div className="grid grid-cols-3 gap-4">
            <div className={t.statCard}>
              <div className="flex items-center justify-between mb-2">
                <p className={t.statLabel}>Total Receipts</p>
                <ReceiptText size={15} className="text-gray-300" />
              </div>
              <p className={t.statValue}>{stats.total}</p>
            </div>

            <div className={t.statCard}>
              <div className="flex items-center justify-between mb-2">
                <p className={t.statLabel}>Needs Review</p>
                <AlertTriangle
                  size={15}
                  className={stats.needReview > 0 ? "text-amber-400" : "text-gray-300"}
                />
              </div>
              <p className={`${t.statValue} ${stats.needReview > 0 ? "text-amber-600" : ""}`}>
                {stats.needReview}
              </p>
            </div>

            <div className={t.statCard}>
              <div className="flex items-center justify-between mb-2">
                <p className={t.statLabel}>Total Spend</p>
                <DollarSign size={15} className="text-gray-300" />
              </div>
              <p className={t.statValue}>{fmtCurrency(stats.totalSpend)}</p>
            </div>
          </div>
        )}

        {/* ── Table card ────────────────────────────────────────────── */}
        <div className={t.card}>
          <div className="flex items-center justify-between px-5 py-4 border-b border-gray-100">
            <div>
              <h2 className="text-sm font-semibold text-gray-900">Receipts</h2>
              {!isLoading && (
                <p className="text-xs text-gray-400 mt-0.5">
                  {docs.length} document{docs.length !== 1 ? "s" : ""}
                </p>
              )}
            </div>
            <button
              onClick={() => refetch()}
              className={t.btnGhost}
              title="Refresh"
            >
              <RefreshCw size={14} className={isLoading ? "animate-spin" : ""} />
            </button>
          </div>

          {isLoading && (
            <div className="flex items-center justify-center py-20 gap-2.5 text-gray-400">
              <RefreshCw size={16} className="animate-spin" />
              <span className="text-sm">Loading…</span>
            </div>
          )}

          {isError && (
            <div className="text-center py-20">
              <p className="text-sm font-medium text-red-500">Failed to load receipts</p>
              <button
                onClick={() => refetch()}
                className="mt-3 text-xs text-brand-600 hover:underline font-medium"
              >
                Try again
              </button>
            </div>
          )}

          {!isLoading && !isError && (
            <DocumentTable
              documents={docs}
              newId={newId}
              onRowClick={setSelected}
            />
          )}
        </div>
      </main>

      {showUpload && (
        <UploadModal
          schemaKey={SCHEMA_KEY}
          onSuccess={handleUploadSuccess}
          onClose={() => setShowUpload(false)}
        />
      )}

      {selected && (
        <DocumentDrawer
          doc={selected}
          onClose={() => setSelected(null)}
          onDocChange={setSelected}
        />
      )}

      {showSettings && (
        <SettingsPanel onClose={() => setShowSettings(false)} />
      )}
    </div>
  );
}
