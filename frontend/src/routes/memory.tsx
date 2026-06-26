import { createFileRoute } from "@tanstack/react-router";
import { Shell, PageHeader, Section } from "@/components/apa/Shell";
import { useApa } from "@/lib/apa/store";

export const Route = createFileRoute("/memory")({
  head: () => ({ meta: [{ title: "Memory Evolution — APA-OS V2" }] }),
  component: MemoryPage,
});

function MemoryPage() {
  const memory = useApa(s => s.memory);
  // count by day for last 14 days
  const days = Array.from({ length: 14 }, (_, i) => {
    const start = Date.now() - (13 - i) * 86400000;
    const end = start + 86400000;
    return { i, count: memory.filter(m => m.createdAt >= start && m.createdAt < end).length };
  });
  const max = Math.max(1, ...days.map(d => d.count));

  return (
    <Shell>
      <PageHeader
        eyebrow="Hidden Layer 06 · 08"
        title="Memory Evolution."
        lede="What the system learned this week — about you, about the people in your world, about how to be more right next time."
      />

      <Section title="Memory growth · last 14 days">
        <div className="flex items-end gap-2 h-32">
          {days.map(d => (
            <div key={d.i} className="flex-1 flex flex-col items-center gap-1">
              <div className="w-full rounded-sm bg-accent" style={{ height: `${(d.count / max) * 100}%`, minHeight: 2 }} />
              <span className="font-mono text-[9px] text-muted-foreground">{14 - d.i}d</span>
            </div>
          ))}
        </div>
      </Section>

      <Section title="Recent memories">
        <ul className="divide-y divide-[var(--color-border)] border hairline rounded-lg overflow-hidden">
          {memory.map(m => (
            <li key={m.id} className="bg-surface/30 px-6 py-4 flex items-baseline gap-6">
              <span className="font-mono text-[10px] uppercase tracking-[0.18em] text-accent w-24 shrink-0">{m.kind}</span>
              <span className="text-[14px] flex-1">{m.text}</span>
              <span className="font-mono text-[10px] text-muted-foreground">
                {new Date(m.createdAt).toLocaleDateString([], { month: "short", day: "numeric" })}
              </span>
            </li>
          ))}
        </ul>
      </Section>
    </Shell>
  );
}
