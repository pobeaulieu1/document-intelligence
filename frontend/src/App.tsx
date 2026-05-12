import { useState } from "react";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { QueryClient, QueryClientProvider, useQueryClient } from "@tanstack/react-query";
import { Navbar } from "./components/Navbar";
import { DocumentsPage } from "./components/DocumentsPage";
import { ReceiptPage } from "./components/ReceiptPage";
import { PolicyPage } from "./components/PolicyPage";
import { PipelinePage } from "./components/PipelinePage";
import { UploadModal } from "./components/UploadModal";
import { ChatPanel } from "./components/ChatPanel";

const SCHEMA_KEY = "receipt";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: { retry: 1, staleTime: 10_000 },
  },
});

export type ChatState = "closed" | "open";

function AppShell() {
  const qc = useQueryClient();
  const [chatState, setChatState] = useState<ChatState>("closed");
  const [isRecomputing, setIsRecomputing] = useState(false);
  const [showUpload, setShowUpload] = useState(false);

  function handleUploadSuccess() {
    setShowUpload(false);
    qc.invalidateQueries({ queryKey: ["documents", SCHEMA_KEY] });
  }

  return (
    <div className="min-h-screen bg-[#f7f8fa] flex flex-col">
      <Navbar onUpload={() => setShowUpload(true)} />

      <div className="flex-1">
        <Routes>
          <Route path="/" element={<DocumentsPage isRecomputing={isRecomputing} />} />
          <Route path="/receipts/:id" element={<ReceiptPage isRecomputing={isRecomputing} />} />
          <Route path="/policy" element={<PolicyPage />} />
          <Route path="/pipeline" element={<PipelinePage />} />
        </Routes>
      </div>

      <ChatPanel
        schemaKey={SCHEMA_KEY}
        state={chatState}
        onStateChange={setChatState}
        onRecomputeStart={() => setIsRecomputing(true)}
        onRecomputeEnd={() => setIsRecomputing(false)}
      />

      {showUpload && (
        <UploadModal
          schemaKey={SCHEMA_KEY}
          onSuccess={handleUploadSuccess}
          onClose={() => setShowUpload(false)}
        />
      )}
    </div>
  );
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <AppShell />
      </BrowserRouter>
    </QueryClientProvider>
  );
}
