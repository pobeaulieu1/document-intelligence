export interface LineItem {
  description: string;
  quantity?: number;
  unit_price: number;
  total: number;
}

export interface ReceiptData {
  merchant_name: string;
  date?: string;
  total_amount: number;
  currency: string;
  payment_method?: string | null;
  line_items: LineItem[];
  [key: string]: unknown;
}

export interface Enrichments {
  category?: string;
  is_compliant?: boolean;
  violations?: string[];
  status?: "accepted" | "needs_review";
  [key: string]: unknown;
}

export interface Extraction {
  id: string;
  schema_key: string;
  file_name?: string | null;
  data: ReceiptData;
  enrichments?: Enrichments | null;
  confidence: number;
  created_at: string;
}

// ── Schema / Policy types ─────────────────────────────────────────────────

export interface PolicyRule {
  id: string;
  text: string;
}

export interface Schema {
  id: string;
  key: string;
  name: string;
  description?: string | null;
  validation_rules?: { rules: PolicyRule[] } | null;
  created_at: string;
  updated_at: string;
}

// ── LLM config types ──────────────────────────────────────────────────────

export interface AgentConfig {
  provider: string;
  model: string;
}

export interface EmbeddingConfig {
  provider: string;
  model: string;
  dimensions: number;
}

export interface LLMConfig {
  agents: Record<string, AgentConfig>;
  embeddings?: EmbeddingConfig | null;
}
