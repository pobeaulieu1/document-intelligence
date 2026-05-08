import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { DocumentsPage } from "./components/DocumentsPage";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: { retry: 1, staleTime: 10_000 },
  },
});

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <DocumentsPage />
    </QueryClientProvider>
  );
}
