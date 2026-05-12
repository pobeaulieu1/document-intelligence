import { useState } from "react";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { DocumentsPage } from "./components/DocumentsPage";
import { ReceiptPage } from "./components/ReceiptPage";
import { ChatPanel } from "./components/ChatPanel";

const SCHEMA_KEY = "receipt";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: { retry: 1, staleTime: 10_000 },
  },
});

export type ChatState = "closed" | "open" | "minimized";

export default function App() {
  const [chatState, setChatState] = useState<ChatState>("closed");
  const [isRecomputing, setIsRecomputing] = useState(false);

  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route
            path="/"
            element={
              <DocumentsPage
                onOpenChat={() => setChatState("open")}
                isRecomputing={isRecomputing}
              />
            }
          />
          <Route path="/receipts/:id" element={<ReceiptPage onOpenChat={() => setChatState("open")} isRecomputing={isRecomputing} />} />
        </Routes>

        <ChatPanel
          schemaKey={SCHEMA_KEY}
          state={chatState}
          onStateChange={setChatState}
          onRecomputeStart={() => setIsRecomputing(true)}
          onRecomputeEnd={() => setIsRecomputing(false)}
        />
      </BrowserRouter>
    </QueryClientProvider>
  );
}
