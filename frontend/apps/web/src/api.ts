import { createApiClient } from "@vb/api-client";

// The backend address. Override with VITE_API_URL (e.g. in apps/web/.env.local).
export const api = createApiClient(import.meta.env.VITE_API_URL ?? "http://localhost:8000");
