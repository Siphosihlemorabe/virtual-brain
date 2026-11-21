// The typed API client. Every path, parameter and response type comes from the generated schema.ts,
// so a backend change that breaks the frontend fails to compile instead of failing at run time.
import createClient from "openapi-fetch";

import type { components, paths } from "./schema";

export type Learner = components["schemas"]["Learner"];

export function createApiClient(baseUrl: string, fetchImpl?: typeof fetch) {
  // fetchImpl lets tests answer requests without a real server.
  return createClient<paths>({ baseUrl, fetch: fetchImpl });
}

export type ApiClient = ReturnType<typeof createApiClient>;
