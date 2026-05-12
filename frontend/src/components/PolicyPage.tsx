import { useId, useEffect, useRef, useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Loader2, CheckCircle2, AlertCircle, Plus, Trash2, RefreshCw } from "lucide-react";
import { getSchema, updateSchemaPolicy, recomputeAll } from "../api";
import { t } from "../theme";
import type { PolicyRule } from "../types";

const SCHEMA_KEY = "receipt";

function AutoTextarea({ id, value, onChange, placeholder }: {
  id: string;
  value: string;
  onChange: (e: React.ChangeEvent<HTMLTextAreaElement>) => void;
  placeholder?: string;
}) {
  const ref = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${el.scrollHeight}px`;
  }, [value]);

  return (
    <textarea
      ref={ref}
      id={id}
      value={value}
      onChange={onChange}
      placeholder={placeholder}
      rows={1}
      className="flex-1 w-full px-4 py-3 text-sm bg-white border border-gray-200 rounded-xl resize-none overflow-hidden
        focus:outline-none focus:ring-2 focus:ring-brand-500/40 focus:border-brand-400
        hover:border-gray-300 transition-all leading-relaxed"
    />
  );
}

export function PolicyPage() {
  const queryClient = useQueryClient();
  const uid = useId();

  const { data: schema, isLoading, isError } = useQuery({
    queryKey: ["schema", SCHEMA_KEY],
    queryFn: () => getSchema(SCHEMA_KEY),
  });

  const [draft, setDraft] = useState<PolicyRule[] | null>(null);
  const [savedBanner, setSavedBanner]     = useState(false);
  const [showRecompute, setShowRecompute] = useState(false);

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
    setDraft([...rules, { id: `rule_${Date.now()}`, text: "" }]);
  }

  function removeRule(id: string) {
    setSavedBanner(false);
    setDraft(rules.filter((r) => r.id !== id));
  }

  if (isLoading) {
    return (
      <main className="max-w-3xl mx-auto px-6 py-8">
        <div className="flex items-center justify-center py-20 gap-2 text-gray-400">
          <Loader2 size={16} className="animate-spin" />
          <span className="text-sm">Loading policy…</span>
        </div>
      </main>
    );
  }

  if (isError) {
    return (
      <main className="max-w-3xl mx-auto px-6 py-8">
        <div className="flex items-center gap-2 p-4 bg-red-50 rounded-xl text-red-600 text-sm border border-red-100">
          <AlertCircle size={14} className="shrink-0" />
          Failed to load policy rules.
        </div>
      </main>
    );
  }

  const isDirty = draft !== null;

  return (
    <main className="max-w-3xl mx-auto px-6 py-8 space-y-6">
      <div>
        <p className="text-sm font-semibold text-gray-900">Expense policy rules</p>
        <p className="text-xs text-gray-400 mt-0.5">
          Write each rule in plain English. The AI reads them and evaluates every new receipt — including context like number of nights or people.
        </p>
      </div>

      <div className="space-y-3">
        {rules.map((rule, idx) => (
          <div key={rule.id} className="flex gap-3 items-start group">
            <span className="mt-3.5 text-xs font-bold text-gray-300 w-5 text-right shrink-0">
              {idx + 1}
            </span>
            <AutoTextarea
              id={`${uid}-rule-${rule.id}`}
              value={rule.text}
              onChange={(e) => updateRule(rule.id, e.target.value)}
              placeholder="e.g. Meals must not exceed $50 per person"
            />
            <button
              onClick={() => removeRule(rule.id)}
              className="mt-3 text-gray-200 hover:text-red-400 transition-colors opacity-0 group-hover:opacity-100 shrink-0"
              title="Remove rule"
            >
              <Trash2 size={15} />
            </button>
          </div>
        ))}
      </div>

      <button
        onClick={addRule}
        className="flex items-center gap-2 text-xs font-semibold text-brand-600 hover:text-brand-700 transition-colors"
      >
        <Plus size={13} />
        Add rule
      </button>

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
                : <><RefreshCw size={13} /> Recompute all receipts</>}
            </button>
            {recomputeMutation.isSuccess && (
              <span className="flex items-center gap-1.5 text-xs text-emerald-600 font-semibold">
                <CheckCircle2 size={13} />
                {recomputeMutation.data.updated} updated
              </span>
            )}
            {!recomputeMutation.isPending && !recomputeMutation.isSuccess && (
              <button onClick={() => setShowRecompute(false)} className="text-xs text-gray-400 hover:text-gray-600 transition-colors">
                Skip
              </button>
            )}
          </div>
        </div>
      )}

      {!showRecompute && (
        <div className="pt-2 border-t border-gray-100">
          <button
            onClick={() => recomputeMutation.mutate()}
            disabled={recomputeMutation.isPending}
            className={`${t.btnGhost} text-xs disabled:opacity-40`}
          >
            {recomputeMutation.isPending
              ? <><Loader2 size={13} className="animate-spin" /> Recomputing…</>
              : <><RefreshCw size={13} /> Recompute all receipts</>}
          </button>
          {recomputeMutation.isSuccess && (
            <span className="ml-3 text-xs text-emerald-600 font-semibold">
              ✓ {recomputeMutation.data.updated} updated
            </span>
          )}
        </div>
      )}
    </main>
  );
}
