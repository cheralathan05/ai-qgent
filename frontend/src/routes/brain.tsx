import { createFileRoute } from "@tanstack/react-router";
import { useMemo, useState } from "react";
import { Shell, PageHeader, Section } from "@/components/apa/Shell";
import { useApa } from "@/lib/apa/store";

export const Route = createFileRoute("/brain")({
  head: () => ({ meta: [{ title: "Second Brain — APA-OS V2" }] }),
  component: BrainPage,
});

function BrainPage() {
  const memory = useApa(s => s.memory);
  const [q, setQ] = useState("");

  const results = useMemo(() => {
    if (!q.trim()) return memory;
    const needle = q.toLowerCase();
    return memory.filter(m => m.text.toLowerCase().includes(needle) || m.kind.includes(needle));
  }, [q, memory]);

  return (
    <Shell>
      <PageHeader
        eyebrow="Hidden Layer 15 — the final evolution"
        title="Second Brain."
        lede="Ask in plain language. The system never asks which folder, which app, which date. It remembers — so you don't have to."
      />
      <Section>
        <input
          value={q}
          onChange={e => setQ(e.target.value)}
          placeholder='Where is that PDF I used last month for ATM Protocol?'
          className="w-full rounded-xl border hairline-strong bg-surface/60 px-5 py-4 font-display text-xl tracking-tight outline-none focus:border-accent transition"
        />

        <ul className="mt-8 divide-y divide-[var(--color-border)] border hairline rounded-lg overflow-hidden">
          {results.length === 0 && (
            <li className="bg-surface/30 px-6 py-8 text-sm text-muted-foreground italic">
              No memories matched. The system would normally widen the search to your chats, drive, and notes — this scaffold is local-only.
            </li>
          )}
          {results.map(m => (
            <li key={m.id} className="bg-surface/30 px-6 py-5">
              <p className="font-mono text-[10px] uppercase tracking-[0.18em] text-accent">{m.kind}</p>
              <p className="mt-2 text-[15px] leading-snug">{m.text}</p>
            </li>
          ))}
        </ul>
      </Section>
    </Shell>
  );
}
