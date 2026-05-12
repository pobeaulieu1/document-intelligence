import { useQuery } from "@tanstack/react-query";
import { Loader2, AlertCircle, ArrowRight } from "lucide-react";
import { getLLMConfig } from "../api";

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
};

export function PipelinePage() {
  const { data: config, isLoading, isError } = useQuery({
    queryKey: ["llm-config"],
    queryFn: getLLMConfig,
  });

  if (isLoading) {
    return (
      <main className="max-w-3xl mx-auto px-6 py-8">
        <div className="flex items-center justify-center py-20 gap-2 text-gray-400">
          <Loader2 size={16} className="animate-spin" />
          <span className="text-sm">Loading…</span>
        </div>
      </main>
    );
  }

  if (isError || !config) {
    return (
      <main className="max-w-3xl mx-auto px-6 py-8">
        <div className="flex items-center gap-2 p-4 bg-red-50 rounded-xl text-red-600 text-sm border border-red-100">
          <AlertCircle size={14} className="shrink-0" />
          Failed to load pipeline configuration.
        </div>
      </main>
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
    <main className="max-w-3xl mx-auto px-6 py-8 space-y-6">
      <div>
        <p className="text-sm font-semibold text-gray-900">Under the hood</p>
        <p className="text-xs text-gray-400 mt-0.5">
          Every receipt flows through {allSteps.length} AI steps, each powered by Anthropic Claude.
        </p>
      </div>

      <div className="space-y-2 max-w-xl">
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
    </main>
  );
}
