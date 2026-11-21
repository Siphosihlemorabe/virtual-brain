import type { ReactNode } from "react";

// A titled box. The basic building block of every screen.
export function Card({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
      <h2 className="mb-2 text-lg font-semibold text-slate-900">{title}</h2>
      <div className="text-slate-700">{children}</div>
    </section>
  );
}
