import "./index.css";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MeCard } from "@vb/ui";
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

import { api } from "./api";

const queryClient = new QueryClient(); // caches API answers and handles loading and retries

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <main className="mx-auto max-w-xl space-y-6 p-8">
        <h1 className="text-2xl font-bold text-slate-900">Virtual Brain</h1>
        <MeCard api={api} />
      </main>
    </QueryClientProvider>
  </StrictMode>,
);
