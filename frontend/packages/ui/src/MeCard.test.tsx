import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { createApiClient } from "@vb/api-client";
import { describe, expect, it } from "vitest";

import { MeCard } from "./MeCard";

function fakeServer(status: number, body: unknown): typeof fetch {
  return async () => new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });
}

function renderWith(fetchImpl: typeof fetch) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } }); // fail fast in tests
  render(
    <QueryClientProvider client={queryClient}>
      <MeCard api={createApiClient("http://api.test", fetchImpl)} />
    </QueryClientProvider>,
  );
}

describe("MeCard", () => {
  it("shows the learner's email once loaded", async () => {
    renderWith(
      fakeServer(200, { id: "1", created_at: "2026-11-20T10:00:00Z", email: "dev@localhost", display_name: null }),
    );
    expect(screen.getByText("Loading…")).toBeInTheDocument();
    expect(await screen.findByText("dev@localhost")).toBeInTheDocument();
  });

  it("shows a clear message when the API is down", async () => {
    renderWith(fakeServer(500, { detail: "boom" }));
    expect(await screen.findByText("Could not reach the Virtual Brain API.")).toBeInTheDocument();
  });
});
