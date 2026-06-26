import { createFileRoute } from "@tanstack/react-router";
import { Shell, PageHeader, Section } from "@/components/apa/Shell";
import { AGENTS } from "@/lib/apa/agents";
import type { AgentId } from "@/lib/apa/types";

export const Route = createFileRoute("/agents/monitor")({
  head: () => ({ meta: [{ title: "Agent Monitor — APA-OS" }] }),
  component: AgentMonitorPage,
});

function AgentMonitorPage() {
  const ids = Object.keys(AGENTS) as AgentId[];
  const rows = ids.map((id, i) => ({
    id,
    name: AGENTS[id].name,
    latency: 80 + ((i * 37) % 220),
    tasks: 12 + ((i * 19) % 80),
    success: 88 + ((i * 7) % 12),
    failures: (i * 3) % 5,
    state: i % 7 === 0 ? "degraded" : "healthy",
  }));

  return (
    <Shell>
      <PageHeader
        eyebrow="Phase 05 · Agents"
        title="Agent Monitor."
        lede="Latency, task volume, success rate, failures — every agent's pulse on one page."
      />

      <Section title={`Live · ${rows.length} agents`}>
        <ul className="divide-y hairline">
          <li className="py-2 grid grid-cols-[1fr_80px_80px_80px_80px_80px] gap-3 text-[9px] uppercase tracking-[0.22em] text-muted-foreground">
            <span>Agent</span><span>State</span><span className="text-right">Latency</span>
            <span className="text-right">Tasks</span><span className="text-right">Success</span><span className="text-right">Failed</span>
          </li>
          {rows.map(r => (
            <li key={r.id} className="py-3 grid grid-cols-[1fr_80px_80px_80px_80px_80px] gap-3 text-[12.5px] items-baseline">
              <span>{r.name}</span>
              <span className={r.state === "healthy" ? "text-[color:var(--color-success)] text-[10px] uppercase tracking-wider" : "text-warn text-[10px] uppercase tracking-wider"}>{r.state}</span>
              <span className="font-mono text-[11px] text-right text-muted-foreground">{r.latency}ms</span>
              <span className="font-mono text-[11px] text-right">{r.tasks}</span>
              <span className="font-mono text-[11px] text-right text-accent">{r.success}%</span>
              <span className="font-mono text-[11px] text-right text-muted-foreground">{r.failures}</span>
            </li>
          ))}
        </ul>
      </Section>
    </Shell>
  );
}
