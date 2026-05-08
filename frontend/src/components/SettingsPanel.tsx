import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  X, Shield, Cpu, ChevronDown, ChevronUp,
  Loader2, CheckCircle2, AlertCircle, ArrowRight,
} from "lucide-react";
import { getSchema, updateSchemaPolicy, getLLMConfig } from "../api";
import { t } from "../theme";
import type { ValidationRule } from "../types";

interface Props {
  onClose: () => void;
}

type Tab = "policy" | "pipeline";

const SCHEMA_KEY = "receipt";

// ── Human labels for rule operators ──────────────────────────────────────
const OPERATOR_LABEL: Record<string, string> = {
  lte: "≤",
  lt:  "<",
  gte: "≥",
  gt:  ">",
  eq:  "=",
  neq: "≠",
  in:  "one of",
  not_in: "not one of",
};

// ── Pretty-print amount limits for the hero number ────────────────────────
function isAmountRule(rule: ValidationRule): boolean {
  return (
    rule.field === "total_amount" &&
    ["lte", "lt", "gte", "gt"].includes(rule.operator) &&
    typeof rule.value === "number"
  );
}

export function SettingsPanel({ onClose }: Props) {
  const [tab, setTab] = useState<Tab>("policy");

  return (
    <>
      <div className="fixed inset-0 z-40 bg-black/20 backdrop-blur-[1px]" onClick={onClose} />

      <aside className="fixed right-0 top-0 bottom-0 z-50 w-[560px] bg-white shadow-2xl flex flex-col animate-slide-in">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-100 shrink-0">
          <h2 className="text-base font-semibold text-gray-900">Settings</h2>
          <button onClick={onClose} className="text-gray-300 hover:text-gray-600 transition-colors">
            <X size={18} />
          </button>
        </div>

        {/* Tabs */}
        <div className="flex border-b border-gray-100 px-6 shrink-0">
          <TabBtn active={tab === "policy"} onClick={() => setTab("policy")} icon={<Shield size={13} />}>
            Expense Policy
          </TabBtn>
          <TabBtn active={tab === "pipeline"} onClick={() => setTab("pipeline")} icon={<Cpu size={13} />}>
            AI Pipeline
          </TabBtn>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto">
          {tab === "policy" && <PolicyEditor />}
          {tab === "pipeline" && <PipelineInfo />}
        </div>
      </aside>
    </>
  );
}

// ── Tab button ────────────────────────────────────────────────────────────
function TabBtn({
  active,
  onClick,
  icon,
  children,
}: {
  active: boolean;
  onClick: () => void;
  icon: React.ReactNode;
  children: React.ReactNode;
}) {
  return (
    <button
      onClick={onClick}
      className={`
        flex items-center gap-1.5 px-4 py-3 text-sm font-semibold border-b-2 transition-colors
        ${active
          ? "border-brand-600 text-brand-600"
          : "border-transparent text-gray-400 hover:text-gray-700"
        }
      `}
    >
      {icon}
      {children}
    </button>
  );
}

// ── Policy editor ─────────────────────────────────────────────────────────
function PolicyEditor() {
  const queryClient = useQueryClient();

  const { data: schema, isLoading, isError } = useQuery({
    queryKey: ["schema", SCHEMA_KEY],
    queryFn: () => getSchema(SCHEMA_KEY),
  });

  const [editedRules, setEditedRules] = useState<ValidationRule[] | null>(null);
  const [saved, setSaved] = useState(false);

  const rules: ValidationRule[] = editedRules ?? (schema?.validation_rules?.rules ?? []);

  const mutation = useMutation({
    mutationFn: () => updateSchemaPolicy(SCHEMA_KEY, rules),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["schema", SCHEMA_KEY] });
      queryClient.invalidateQueries({ queryKey: ["documents"] });
      setEditedRules(null);
      setSaved(true);
      setTimeout(() => setSaved(false), 2500);
    },
  });

  function patchRule(id: string, patch: Partial<ValidationRule>) {
    setSaved(false);
    setEditedRules(
      rules.map((r) => (r.id === id ? { ...r, ...patch } : r))
    );
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-20 gap-2 text-gray-400">
        <Loader2 size={16} className="animate-spin" />
        <span className="text-sm">Loading policy…</span>
      </div>
    );
  }

  if (isError) {
    return (
      <div className="flex items-center gap-2 mx-6 mt-6 p-4 bg-red-50 rounded-xl text-red-600 text-sm border border-red-100">
        <AlertCircle size={14} className="shrink-0" />
        Failed to load policy rules.
      </div>
    );
  }

  const isDirty = editedRules !== null;

  return (
    <div className="px-6 py-6 space-y-4">
      <div>
        <p className="text-sm font-semibold text-gray-900">Spending limits & rules</p>
        <p className="text-xs text-gray-400 mt-0.5">
          Edit limits directly. The AI validates every new receipt against these rules automatically.
        </p>
      </div>

      {rules.map((rule) => (
        <RuleCard key={rule.id} rule={rule} onChange={(patch) => patchRule(rule.id, patch)} />
      ))}

      {/* Save bar */}
      <div className="pt-2 flex items-center gap-3">
        <button
          onClick={() => mutation.mutate()}
          disabled={!isDirty || mutation.isPending}
          className={`${t.btnPrimary} disabled:opacity-40 disabled:cursor-not-allowed`}
        >
          {mutation.isPending ? <Loader2 size={14} className="animate-spin" /> : null}
          Save changes
        </button>
        {saved && (
          <span className="flex items-center gap-1.5 text-xs text-emerald-600 font-semibold">
            <CheckCircle2 size={13} />
            Saved
          </span>
        )}
        {isDirty && !mutation.isPending && (
          <button
            onClick={() => setEditedRules(null)}
            className="text-xs text-gray-400 hover:text-gray-600 transition-colors"
          >
            Discard
          </button>
        )}
      </div>
    </div>
  );
}

// ── Single rule card ──────────────────────────────────────────────────────
function RuleCard({
  rule,
  onChange,
}: {
  rule: ValidationRule;
  onChange: (patch: Partial<ValidationRule>) => void;
}) {
  const [open, setOpen] = useState(false);
  const conditionCategory =
    rule.condition?.field === "category" ? String(rule.condition.value) : null;

  return (
    <div className="rounded-xl border border-gray-100 bg-gray-50 overflow-hidden">
      {/* Summary row */}
      <button
        onClick={() => setOpen((o) => !o)}
        className="w-full flex items-center gap-3 px-4 py-3.5 text-left hover:bg-gray-100/60 transition-colors"
      >
        {conditionCategory && (
          <span className="text-xs font-bold text-gray-500 uppercase tracking-wider w-28 shrink-0 capitalize">
            {conditionCategory}
          </span>
        )}
        <span className="flex-1 text-sm text-gray-700 font-medium truncate">
          {rule.description ?? rule.message}
        </span>
        {isAmountRule(rule) && (
          <span className="text-sm font-bold text-brand-600 tabular-nums shrink-0">
            {OPERATOR_LABEL[rule.operator]} ${rule.value as number}
          </span>
        )}
        {open ? <ChevronUp size={14} className="text-gray-400 shrink-0" /> : <ChevronDown size={14} className="text-gray-400 shrink-0" />}
      </button>

      {/* Expanded edit form */}
      {open && (
        <div className="px-4 pb-4 pt-1 space-y-3 border-t border-gray-100 bg-white">
          {rule.description !== undefined && (
            <Label label="Description">
              <input
                type="text"
                value={rule.description ?? ""}
                onChange={(e) => onChange({ description: e.target.value })}
                className={inputCls}
              />
            </Label>
          )}

          {isAmountRule(rule) && (
            <Label label="Limit (USD)">
              <div className="relative">
                <span className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 text-sm">$</span>
                <input
                  type="number"
                  min={0}
                  value={rule.value as number}
                  onChange={(e) => onChange({ value: Number(e.target.value) })}
                  className={`${inputCls} pl-7`}
                />
              </div>
            </Label>
          )}

          <Label label="Violation message">
            <input
              type="text"
              value={rule.message}
              onChange={(e) => onChange({ message: e.target.value })}
              className={inputCls}
            />
          </Label>
        </div>
      )}
    </div>
  );
}

const inputCls =
  "w-full px-3 py-2 text-sm bg-gray-50 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-brand-500/40 focus:border-brand-400 transition-all";

function Label({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <p className="text-xs font-semibold text-gray-400 mb-1.5">{label}</p>
      {children}
    </div>
  );
}

// ── Pipeline info ─────────────────────────────────────────────────────────

const AGENT_META: Record<string, { title: string; description: string; color: string }> = {
  extraction: {
    title: "Extraction Agent",
    description:
      "Reads the uploaded document (image or PDF) and extracts structured data: merchant name, total amount, date, currency, payment method, and individual line items.",
    color: "bg-brand-50 border-brand-200 text-brand-700",
  },
  enrichment: {
    title: "Enrichment Agent",
    description:
      "Classifies the expense into a category (meals, transport, accommodation, equipment) then validates it against every rule in your expense policy. Sets the final status to Accepted or Needs Review.",
    color: "bg-emerald-50 border-emerald-200 text-emerald-700",
  },
};

function PipelineInfo() {
  const { data: config, isLoading, isError } = useQuery({
    queryKey: ["llm-config"],
    queryFn: getLLMConfig,
  });

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-20 gap-2 text-gray-400">
        <Loader2 size={16} className="animate-spin" />
        <span className="text-sm">Loading pipeline info…</span>
      </div>
    );
  }

  if (isError || !config) {
    return (
      <div className="flex items-center gap-2 mx-6 mt-6 p-4 bg-red-50 rounded-xl text-red-600 text-sm border border-red-100">
        <AlertCircle size={14} className="shrink-0" />
        Failed to load pipeline configuration.
      </div>
    );
  }

  const agentEntries = Object.entries(config.agents);

  return (
    <div className="px-6 py-6 space-y-6">
      <div>
        <p className="text-sm font-semibold text-gray-900">Under the hood</p>
        <p className="text-xs text-gray-400 mt-0.5">
          Each receipt flows through {agentEntries.length} AI agents powered by Anthropic Claude.
        </p>
      </div>

      {/* Pipeline flow */}
      <div className="space-y-3">
        {agentEntries.map(([key, agent], idx) => {
          const meta = AGENT_META[key] ?? {
            title: key.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase()) + " Agent",
            description: "",
            color: "bg-gray-50 border-gray-200 text-gray-700",
          };
          return (
            <div key={key}>
              <div className={`rounded-xl border p-4 space-y-3 ${meta.color}`}>
                {/* Step header */}
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <div className="flex items-center gap-2 mb-1">
                      <span className="text-[10px] font-bold opacity-60 uppercase tracking-widest">
                        Step {idx + 1}
                      </span>
                    </div>
                    <p className="text-sm font-bold">{meta.title}</p>
                  </div>
                  {/* Model chip */}
                  <div className="shrink-0 text-right">
                    <p className="text-[10px] font-semibold opacity-60 uppercase tracking-wider mb-0.5">Model</p>
                    <p className="text-xs font-mono font-bold">{agent.model}</p>
                    <p className="text-[10px] opacity-60 capitalize mt-0.5">{agent.provider}</p>
                  </div>
                </div>
                <p className="text-xs leading-relaxed opacity-80">{meta.description}</p>
              </div>

              {/* Arrow connector */}
              {idx < agentEntries.length - 1 && (
                <div className="flex justify-center py-1">
                  <ArrowRight size={14} className="text-gray-300 rotate-90" />
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Embeddings note */}
      {config.embeddings && config.embeddings.provider !== "none" && (
        <div className="rounded-xl border border-gray-100 bg-gray-50 p-4 space-y-1">
          <p className="text-xs font-bold text-gray-500 uppercase tracking-wider">Embeddings</p>
          <p className="text-sm font-semibold text-gray-800">{config.embeddings.model}</p>
          <p className="text-xs text-gray-400">
            {config.embeddings.dimensions}-dimension vectors stored per receipt for semantic search.
          </p>
        </div>
      )}
    </div>
  );
}
