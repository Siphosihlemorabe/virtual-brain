import { describe, expect, it } from "vitest";

import { createApiClient } from "./index";

describe("api client", () => {
  it("calls /v1/me and returns the learner, typed", async () => {
    const requested: string[] = [];
    const fakeFetch: typeof fetch = async (input) => {
      requested.push(input instanceof Request ? input.url : String(input));
      const learner = { id: "1", created_at: "2026-11-20T10:00:00Z", email: "dev@localhost", display_name: null };
      return new Response(JSON.stringify(learner), { status: 200, headers: { "Content-Type": "application/json" } });
    };

    const { data } = await createApiClient("http://api.test", fakeFetch).GET("/v1/me");

    expect(requested).toEqual(["http://api.test/v1/me"]);
    expect(data?.email).toBe("dev@localhost");
  });
});
