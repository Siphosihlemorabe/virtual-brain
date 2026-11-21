import "./index.css";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { createApiClient } from "@vb/api-client";
import { MeCard } from "@vb/ui";
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

// host_permissions in the manifest let the extension call this address directly.
const api = createApiClient(import.meta.env.VITE_API_URL ?? "http://localhost:8000");
const queryClient = new QueryClient();

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <main className="space-y-4 p-4">
        <h1 className="text-xl font-bold text-slate-900">Virtual Brain</h1>
        <MeCard api={api} />
      </main>
    </QueryClientProvider>
  </StrictMode>,
);
