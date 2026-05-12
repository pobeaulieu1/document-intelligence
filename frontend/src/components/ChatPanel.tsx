import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { X, Send, MessageSquare, Loader2, Minus } from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { chatWithDocuments } from "../api";
import type { ChatState } from "../App";

interface Message {
  role: "user" | "assistant";
  content: string;
}

interface Props {
  schemaKey: string;
  state: ChatState;
  onStateChange: (s: ChatState) => void;
}

export function ChatPanel({ schemaKey, state, onStateChange }: Props) {
  const navigate = useNavigate();
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (state === "open") {
      bottomRef.current?.scrollIntoView({ behavior: "smooth" });
    }
  }, [messages, isLoading, state]);

  async function handleSend() {
    const text = input.trim();
    if (!text || isLoading) return;
    setInput("");
    setMessages((prev) => [...prev, { role: "user", content: text }]);
    setIsLoading(true);
    try {
      const { answer } = await chatWithDocuments(schemaKey, text);
      setMessages((prev) => [...prev, { role: "assistant", content: answer }]);
    } catch {
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: "Something went wrong. Please try again." },
      ]);
    } finally {
      setIsLoading(false);
    }
  }

  const lastMsg = messages[messages.length - 1];

  // ── FAB ──────────────────────────────────────────────────────────────────
  if (state === "closed") {
    return (
      <div className="fixed bottom-6 right-6 z-50">
        <button
          onClick={() => onStateChange("open")}
          className="relative w-14 h-14 bg-brand-600 hover:bg-brand-700 text-white rounded-full shadow-modal flex items-center justify-center transition-colors"
          title="Ask AI"
        >
          <MessageSquare size={22} />
          {messages.length > 0 && (
            <span className="absolute -top-1 -right-1 w-5 h-5 bg-red-500 text-white text-[10px] font-bold rounded-full flex items-center justify-center">
              {messages.filter((m) => m.role === "assistant").length}
            </span>
          )}
        </button>
      </div>
    );
  }

  // ── Minimized header bar ──────────────────────────────────────────────────
  if (state === "minimized") {
    return (
      <div className="fixed bottom-6 right-6 z-50 w-[520px]">
        <div
          className="flex items-center justify-between px-4 h-12 bg-brand-600 text-white rounded-2xl shadow-modal cursor-pointer select-none"
          onClick={() => onStateChange("open")}
        >
          <div className="flex items-center gap-2 min-w-0">
            <MessageSquare size={15} className="shrink-0" />
            <span className="text-sm font-semibold truncate">
              {lastMsg ? lastMsg.content.slice(0, 40) + (lastMsg.content.length > 40 ? "…" : "") : "Ask your receipts"}
            </span>
          </div>
          <div className="flex items-center gap-1 shrink-0 ml-2">
            <button
              onClick={(e) => { e.stopPropagation(); onStateChange("open"); }}
              className="p-1 rounded hover:bg-white/20 transition-colors"
              title="Expand"
            >
              <MessageSquare size={14} />
            </button>
            <button
              onClick={(e) => { e.stopPropagation(); onStateChange("closed"); }}
              className="p-1 rounded hover:bg-white/20 transition-colors"
              title="Close"
            >
              <X size={14} />
            </button>
          </div>
        </div>
      </div>
    );
  }

  // ── Open (full panel) ─────────────────────────────────────────────────────
  return (
    <div className="fixed bottom-6 right-6 z-50 w-[520px] flex flex-col bg-white rounded-2xl shadow-modal overflow-hidden animate-slide-in" style={{ height: "680px" }}>
      {/* Header */}
      <div className="shrink-0 flex items-center justify-between px-4 h-12 bg-brand-600 text-white">
        <div className="flex items-center gap-2">
          <MessageSquare size={15} />
          <span className="text-sm font-semibold">Ask your receipts</span>
        </div>
        <div className="flex items-center gap-1">
          <button
            onClick={() => onStateChange("minimized")}
            className="p-1 rounded hover:bg-white/20 transition-colors"
            title="Minimize"
          >
            <Minus size={14} />
          </button>
          <button
            onClick={() => onStateChange("closed")}
            className="p-1 rounded hover:bg-white/20 transition-colors"
            title="Close"
          >
            <X size={14} />
          </button>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4 bg-gray-50">
        {messages.length === 0 && (
          <div className="flex flex-col items-center justify-center text-center gap-3 h-full">
            <MessageSquare size={28} className="text-gray-200" />
            <p className="text-sm text-gray-400">
              Ask anything about your receipts.
              <br />
              <span className="text-xs text-gray-400">e.g. "What did I spend on meals?"</span>
            </p>
          </div>
        )}

        {messages.map((m, i) => (
          <div key={i} className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}>
            <div
              className={`max-w-[85%] px-3.5 py-2.5 rounded-2xl text-sm leading-relaxed ${
                m.role === "user"
                  ? "bg-brand-600 text-white rounded-br-sm"
                  : "bg-white text-gray-900 rounded-bl-sm shadow-card prose prose-sm prose-a:text-brand-600 prose-a:font-medium prose-a:no-underline hover:prose-a:underline prose-table:text-xs prose-td:py-1 prose-th:py-1 max-w-none"
              }`}
            >
              {m.role === "assistant" ? (
                <ReactMarkdown
                  remarkPlugins={[remarkGfm]}
                  components={{
                    a({ href, children }) {
                      if (href?.startsWith("/receipts/")) {
                        return (
                          <button
                            onClick={() => navigate(href)}
                            className="text-brand-600 font-medium hover:underline"
                          >
                            {children}
                          </button>
                        );
                      }
                      return (
                        <a href={href} target="_blank" rel="noopener noreferrer">
                          {children}
                        </a>
                      );
                    },
                  }}
                >
                  {m.content}
                </ReactMarkdown>
              ) : (
                m.content
              )}
            </div>
          </div>
        ))}

        {isLoading && (
          <div className="flex justify-start">
            <div className="bg-white rounded-2xl rounded-bl-sm px-4 py-3 shadow-card">
              <Loader2 size={14} className="text-gray-400 animate-spin" />
            </div>
          </div>
        )}

        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <div className="shrink-0 border-t border-gray-100 p-3 bg-white">
        <div className="flex gap-2">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && handleSend()}
            placeholder="Ask a question…"
            disabled={isLoading}
            className="flex-1 text-sm bg-gray-50 border border-gray-200 rounded-xl px-3.5 py-2 outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-100 disabled:opacity-50 placeholder-gray-400"
          />
          <button
            onClick={handleSend}
            disabled={!input.trim() || isLoading}
            className="w-9 h-9 bg-brand-600 hover:bg-brand-700 disabled:opacity-40 disabled:cursor-not-allowed text-white rounded-xl flex items-center justify-center transition-colors"
          >
            <Send size={14} />
          </button>
        </div>
      </div>
    </div>
  );
}
