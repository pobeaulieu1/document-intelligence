import { t } from "../theme";
import { StatusBadge } from "./StatusBadge";
import type { Extraction } from "../types";

interface Props {
  documents: Extraction[];
  newId?: string;
  onRowClick: (doc: Extraction) => void;
}

function relativeTime(iso: string) {
  const diff = Date.now() - new Date(iso).getTime();
  const m = Math.floor(diff / 60_000);
  if (m < 60) return `${m}m ago`;
  const h = Math.floor(m / 60);
  if (h < 24) return `${h}h ago`;
  return `${Math.floor(h / 24)}d ago`;
}

function fmtAmount(n: number, currency: string) {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: currency || "USD",
  }).format(n);
}

function fmtDate(iso?: string) {
  if (!iso) return "—";
  return new Date(iso).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

function fmtPayment(v?: string | null) {
  if (!v) return "—";
  return v.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

export function DocumentTable({ documents, newId, onRowClick }: Props) {
  if (documents.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-24 text-gray-400 gap-2">
        <svg
          className="w-10 h-10 text-gray-200"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          strokeWidth={1.5}
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            d="M9 12h3.75M9 15h3.75M9 18h3.75m3 .75H18a2.25 2.25 0 002.25-2.25V6.108c0-1.135-.845-2.098-1.976-2.192a48.424 48.424 0 00-1.123-.08m-5.801 0c-.065.21-.1.433-.1.664 0 .414.336.75.75.75h4.5a.75.75 0 00.75-.75a2.25 2.25 0 00-.1-.664m-5.8 0A2.251 2.251 0 0113.5 2.25H15c1.012 0 1.867.668 2.15 1.586m-5.8 0c-.376.023-.75.05-1.124.08C9.095 4.01 8.25 4.973 8.25 6.108V8.25m0 0H4.875c-.621 0-1.125.504-1.125 1.125v11.25c0 .621.504 1.125 1.125 1.125h9.75c.621 0 1.125-.504 1.125-1.125V9.375c0-.621-.504-1.125-1.125-1.125H8.25z"
          />
        </svg>
        <p className="text-sm font-medium text-gray-500">No receipts yet</p>
        <p className="text-xs">Upload your first document to get started.</p>
      </div>
    );
  }

  return (
    <table className="w-full">
      <thead>
        <tr className="border-b border-gray-100">
          {["Merchant", "Status", "Category", "Amount", "Date", "Payment", "Uploaded"].map(
            (col) => (
              <th key={col} className={t.tableHead}>
                {col}
              </th>
            )
          )}
        </tr>
      </thead>
      <tbody>
        {documents.map((doc) => (
          <tr
            key={doc.id}
            onClick={() => onRowClick(doc)}
            className={`
              cursor-pointer border-b border-gray-50 last:border-0
              hover:bg-gray-50/70 transition-colors group
              ${doc.id === newId ? "animate-new-row" : ""}
            `}
          >
            <td className={`${t.tableCell} font-semibold text-gray-900 max-w-[200px]`}>
              <span className="truncate block">{doc.data.merchant_name}</span>
            </td>
            <td className={t.tableCell}>
              <StatusBadge status={doc.enrichments?.status} />
            </td>
            <td className={`${t.tableCell} capitalize text-gray-500`}>
              {doc.enrichments?.category ?? "—"}
            </td>
            <td className={`${t.tableCell} font-semibold text-gray-900 tabular-nums`}>
              {fmtAmount(doc.data.total_amount, doc.data.currency)}
            </td>
            <td className={`${t.tableCell} text-gray-500`}>
              {fmtDate(doc.data.date)}
            </td>
            <td className={`${t.tableCell} text-gray-500`}>
              {fmtPayment(doc.data.payment_method)}
            </td>
            <td className={`${t.tableCell} text-gray-400 text-xs`}>
              {relativeTime(doc.created_at)}
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
