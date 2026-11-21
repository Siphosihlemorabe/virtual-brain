import { useQuery } from "@tanstack/react-query";
import type { ApiClient } from "@vb/api-client";

import { Card } from "./Card";

// Shows who the API says you are. The client is passed in, so tests can give it a fake server.
export function MeCard({ api }: { api: ApiClient }) {
  const me = useQuery({
    queryKey: ["me"],
    queryFn: async () => {
      const { data } = await api.GET("/v1/me");
      if (!data) throw new Error("Could not reach the Virtual Brain API.");
      return data;
    },
  });

  return (
    <Card title="Who am I">
      {me.isPending && <p>Loading…</p>}
      {me.isError && <p className="text-red-700">{me.error.message}</p>}
      {me.data && (
        <p>
          You are <strong>{me.data.email ?? "a learner with no email yet"}</strong>
        </p>
      )}
    </Card>
  );
}
