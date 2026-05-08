import { useId, useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  X, Shield, Cpu, Loader2, CheckCircle2, AlertCircle,
  ArrowRight, Plus, Trash2, RefreshCw,
} from "lucide-react";
import { getSchema, updateSchemaPolicy, recomputeAll, getLLMConfig } from "../api";
import { t } from "../theme";
import type { PolicyRule } from "../types";

interface Props {
  onClose: () => void;
}

type Tab = "policy" | "pipeline";

const SCHEMA_KEY = "receipt";

export function SettingsPanel({ onClose }: Props) {
  const [tab, setTab] = useState<Tab>("policy");

  return (
    <>
      <div className="fixed inset-0 z-40 bg-black/20 backdrop-blur-[1px]" onClick={onClose} />

      <aside className="fixed right-0 top-0 bottom-0 z-50 w-[540px] bg-white shadow-2xl flex flex-col animate-slide-in">
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-100 shrink-0">
          <h2 className="text-base font-semibold text-gray-900">Settings</h2>
          <button onClick={onClose} className="text-gray-300 hover:text-gray-600 transition-colors">
            <X size={18} />
          </button>
        </div>

        <div className="flex border-b border-gray-100 px-6 shrink-0">
          <TabBtn active={tab === "policy"} onClick={() => setTab("policy")} icon={<Shield size={13} />}>
            Expense Policy
          </TabBtn>
          <TabBtn active={tab === "pipeline"} onClick={() => setTab("pipeline")} icon={<Cpu size={13} />}>
            AI Pipeline
          </TabBtn>
        </div>

        <div className="flex-1 overflow-y-auto">
          {tab === "policy"   && <PolicyEditor />}
          {tab === "pipeline" && <PipelineInfo />}
        </div>
      </aside>
    </>
  );
}

function TabBtn({
  active, onClick, icon, children,
}: {
  active: boolean; onClick: () => void; icon: React.ReactNode; children: React.ReactNode;
}) {
  return (
    <button
      onClick={onClick}
      className={`flex items-center gap-1.5 px-4 py-3 text-sm font-semibold border-b-2 transition-colors
        ${active ? "border-brand-600 text-brand-600" : "border-transparent text-gray-400 hover:text-gray-700"}`}
    >
      {icon}{children}
    </button>
  );
}

// ── Policy editor ─────────────────────────────────────────────────────────

function PolicyEditor() {
  const queryClient = useQueryClient();
  const uid = useId();

  const { data: schema, isLoading, isError } = useQuery({
    queryKey: ["schema", SCHEMA_KEY],
    queryFn: () => getSchema(SCHEMA_KEY),
  });

  const [draft, setDraft] = useState<PolicyRule[] | null>(null);
  const [savedBanner, setSavedBanner]       = useState(false);
  const [showRecompute, setShowRecompute]   = useState(false);

  const rules: PolicyRule[] = draft ?? (schema?.validation_rules?.rules ?? []);

  const saveMutation = useMutation({
    mutationFn: () => updateSchemaPolicy(SCHEMA_KEY, rules),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["schema", SCHEMA_KEY] });
      setDraft(null);
      setSavedBanner(true);
      setShowRecompute(true);
    },
  });

  const recomputeMutation = useMutation({
    mutationFn: () => recomputeAll(SCHEMA_KEY),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["documents", SCHEMA_KEY] });
      setShowRecompute(false);
    },
  });

  function updateRule(id: string, text: string) {
    setSavedBanner(false);
    setDraft(rules.map((r) => (r.id === id ? { ...r, text } : r)));
  }

  function addRule() {
    setSavedBanner(false);
    const newId = `rule_${Date.now()}`;
    setDraft([...rules, { id: newId, text: "" }]);
  }

  function removeRule(id: string) {
    setSavedBanner(false);
    setDraft(rules.filter((r) => r.id !== id));
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

  const isDirty = draft !== null;

  return (
    <div className="px-6 py-6 space-y-4">
      {/* Header */}
      <div>
        <p className="text-sm font-semibold text-gray-900">Expense policy rules</p>
        <p className="text-xs text-gray-400 mt-0.5">
          Write each rule in plain English. The AI reads them and evaluates every new receipt — including context like number of nights or people.
        </p>
      </div>

      {/* Rules list */}
      <div className="space-y-2">
        {rules.map((rule, idx) => (
          <div key={rule.id} className="flex gap-2 items-start group">
            <span className="mt-2.5 text-xs font-bold text-gray-300 w-5 text-right shrink-0">
              {idx + 1}
            </span>
            <textarea
              id={`${uid}-rule-${rule.id}`}
              value={rule.text}
              onChange={(e) => updateRule(rule.id, e.target.value)}
              rows={2}
              placeholder="e.g. Meals must not exceed $50 per person"
              className="flex-1 px-3 py-2 text-sm bg-gray-50 border border-gray-200 rounded-xl resize-none
                focus:outline-none focus:ring-2 focus:ring-brand-500/40 focus:border-brand-400
                hover:border-gray-300 transition-all leading-relaxed"
            />
            <button
              onClick={() => removeRule(rule.id)}
              className="mt-2 text-gray-200 hover:text-red-400 transition-colors opacity-0 group-hover:opacity-100"
              title="Remove rule"
            >
              <Trash2 size={14} />
            </button>
          </div>
        ))}
      </div>

      {/* Add rule */}
      <button
        onClick={addRule}
        className="flex items-center gap-2 text-xs font-semibold text-brand-600 hover:text-brand-700 transition-colors"
      >
        <Plus size={13} />
        Add rule
      </button>

      {/* Save bar */}
      <div className="flex items-center gap-3 pt-1">
        <button
          onClick={() => saveMutation.mutate()}
          disabled={!isDirty || saveMutation.isPending}
          className={`${t.btnPrimary} disabled:opacity-40 disabled:cursor-not-allowed`}
        >
          {saveMutation.isPending && <Loader2 size={14} className="animate-spin" />}
          Save changes
        </button>
        {savedBanner && !isDirty && (
          <span className="flex items-center gap-1.5 text-xs text-emerald-600 font-semibold">
            <CheckCircle2 size={13} />
            Saved
          </span>
        )}
        {isDirty && (
          <button
            onClick={() => { setDraft(null); setSavedBanner(false); }}
            className="text-xs text-gray-400 hover:text-gray-600 transition-colors"
          >
            Discard
          </button>
        )}
      </div>

      {/* Recompute prompt */}
      {showRecompute && !isDirty && (
        <div className="rounded-xl border border-brand-200 bg-brand-50 p-4 space-y-3">
          <div>
            <p className="text-sm font-semibold text-brand-800">Policy saved</p>
            <p className="text-xs text-brand-600 mt-0.5">
              Recompute existing receipts against the new rules? The AI will re-evaluate every receipt already in the system.
            </p>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => recomputeMutation.mutate()}
              disabled={recomputeMutation.isPending}
              className={`${t.btnPrimary} text-xs px-3 py-2 disabled:opacity-40`}
            >
              {recomputeMutation.isPending
                ? <><Loader2 size={13} className="animate-spin" /> Recomputing…</>
                : <><RefreshCw size={13} /> Recompute all receipts</>
              }
            </button>
            {recomputeMutation.isSuccess && (
              <span className="flex items-center gap-1.5 text-xs text-emerald-600 font-semibold">
                <CheckCircle2 size={13} />
                {recomputeMutation.data.updated} updated
              </span>
            )}
            {!recomputeMutation.isPending && !recomputeMutation.isSuccess && (
              <button
                onClick={() => setShowRecompute(false)}
                className="text-xs text-gray-400 hover:text-gray-600 transition-colors"
              >
                Skip
              </button>
            )}
          </div>
        </div>
      )}

      {/* Standalone recompute button (always available) */}
      {!showRecompute && (
        <div className="pt-2 border-t border-gray-100">
          <button
            onClick={() => recomputeMutation.mutate()}
            disabled={recomputeMutation.isPending}
            className={`${t.btnGhost} text-xs disabled:opacity-40`}
          >
            {recomputeMutation.isPending
              ? <><Loader2 size={13} className="animate-spin" /> Recomputing…</>
              : <><RefreshCw size={13} /> Recompute all receipts</>
            }
          </button>
          {recomputeMutation.isSuccess && (
            <span className="ml-3 text-xs text-emerald-600 font-semibold">
              ✓ {recomputeMutation.data.updated} updated
            </span>
          )}
        </div>
      )}
    </div>
  );
}

// ── Pipeline info ─────────────────────────────────────────────────────────

const AGENT_META: Record<string, { title: string; description: string; color: string }> = {
  extraction: {
    title: "Extraction Agent",
    description:
      "Reads the uploaded document (image or PDF) using vision and extracts structured data: merchant name, total amount, date, currency, payment method, number of nights or people when visible, and individual line items.",
    color: "bg-brand-50 border-brand-200 text-brand-700",
  },
  enrichment: {
    title: "Enrichment Agent",
    description:
      "Classifies the expense into a category (meals, transport, accommodation, equipment) based on semantic understanding of the merchant and line items.",
    color: "bg-sky-50 border-sky-200 text-sky-700",
  },
};

const VALIDATION_META = {
  title: "Policy Validation Agent",
  description:
    "Evaluates the expense against your plain-English policy rules. Reasons contextually — a $900 hotel stay for 3 nights is $300/night. Returns accepted or needs_review with specific violation messages.",
  color: "bg-emerald-50 border-emerald-200 text-emerald-700",
  model: "same as Enrichment",
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
        <span className="text-sm">Loading…</span>
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
  const allSteps = [
    ...agentEntries.map(([key, agent]) => ({
      key,
      meta: AGENT_META[key] ?? {
        title: `${key.charAt(0).toUpperCase() + key.slice(1)} Agent`,
        description: "",
        color: "bg-gray-50 border-gray-200 text-gray-700",
      },
      model: agent.model,
      provider: agent.provider,
    })),
    {
      key: "validation",
      meta: VALIDATION_META,
      model: config.agents["enrichment"]?.model ?? "—",
      provider: config.agents["enrichment"]?.provider ?? "anthropic",
    },
  ];

  return (
    <div className="px-6 py-6 space-y-6">
      <div>
        <p className="text-sm font-semibold text-gray-900">Under the hood</p>
        <p className="text-xs text-gray-400 mt-0.5">
          Every receipt flows through {allSteps.length} AI steps, each powered by Anthropic Claude.
        </p>
      </div>

      <div className="space-y-2">
        {allSteps.map((step, idx) => (
          <div key={step.key}>
            <div className={`rounded-xl border p-4 space-y-2.5 ${step.meta.color}`}>
              <div className="flex items-start justify-between gap-3">
                <div>
                  <p className="text-[10px] font-bold opacity-50 uppercase tracking-widest mb-0.5">
                    Step {idx + 1}
                  </p>
                  <p className="text-sm font-bold">{step.meta.title}</p>
                </div>
                <div className="shrink-0 text-right">
                  <p className="text-[10px] font-semibold opacity-50 uppercase tracking-wider mb-0.5">Model</p>
                  <p className="text-xs font-mono font-bold leading-tight">{step.model}</p>
                  <p className="text-[10px] opacity-50 capitalize mt-0.5">{step.provider}</p>
                </div>
              </div>
              <p className="text-xs leading-relaxed opacity-75">{step.meta.description}</p>
            </div>
            {idx < allSteps.length - 1 && (
              <div className="flex justify-center py-0.5">
                <ArrowRight size={13} className="text-gray-300 rotate-90" />
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
