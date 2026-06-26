import { createFileRoute } from "@tanstack/react-router";
import { Shell, PageHeader, Section } from "@/components/apa/Shell";
import { useApa } from "@/lib/apa/store";
import { AGENTS, AGENT_LIST } from "@/lib/apa/agents";
import type { AgentId, AgentStatus } from "@/lib/apa/types";

export const Route = createFileRoute("/agents")({
  head: () => ({ meta: [{ title: "Agent Mission Control — APA-OS V3" }] }),
  component: AgentsPage,
});

function AgentsPage() {
  const outcomes = useApa(s => s.outcomes);
  const focused = outcomes[0];

  const liveAgents = AGENT_LIST.map(a => {
    const run = focused?.agents.find(r => r.agentId === a.id);
    return { ...a, status: (run?.status ?? "idle") as AgentStatus, conf: run?.confidence };
  });
  const overallConf = focused
    ? Math.round(focused.agents.reduce((s, a) => s + (a.confidence ?? 75), 0) / Math.max(1, focused.agents.length))
    : 0;

  return (
    <Shell>
      <PageHeader
        eyebrow="Hidden Layer 01"
        title="Agent Mission Control."
        lede="Live floor of ten specialised agents. Watch them think, talk, plan, execute, and verify in real time."
      />

      {/* Live agent floor */}
      <Section title="Active now" aside={focused && (
        <p className="font-mono text-[10px] uppercase tracking-wider text-muted-foreground">
          overall confidence <span className="text-accent">{overallConf}%</span>
        </p>
      )}>
        <ul className="grid grid-cols-2 md:grid-cols-5 gap-px bg-[var(--color-border)] border hairline">
          {liveAgents.map(a => (
            <li key={a.id} className="bg-background p-5">
              <div className="flex items-center gap-2">
                <Dot s={a.status} />
                <p className="text-[13px]">{a.name.replace(" Agent","")}</p>
              </div>
              <p className="mt-1.5 text-[11px] text-muted-foreground leading-snug line-clamp-2">{a.role}</p>
              <div className="mt-3 flex items-center justify-between font-mono text-[9.5px] uppercase tracking-wider">
                <span className="text-muted-foreground">{a.status}</span>
                {a.conf && <span className="text-accent">{a.conf}%</span>}
              </div>
            </li>
          ))}
        </ul>
      </Section>

      {/* Conversation */}
      <Section title="Agent conversation">
        {!focused ? (
          <p className="text-sm text-muted-foreground italic">No outcome in flight. Run one from the Console to see agents collaborate.</p>
        ) : focused.conversation.length === 0 ? (
          <p className="text-sm text-muted-foreground italic">Agents are queuing up…</p>
        ) : (
          <ul className="space-y-3 max-w-3xl">
            {focused.conversation.map((m, i) => (
              <li key={i} className="apa-fade-up flex items-baseline gap-4 border-b hairline pb-3">
                <span className="font-mono text-[9.5px] uppercase tracking-wider text-accent w-32 shrink-0">
                  {AGENTS[m.from].name.replace(" Agent","")}
                  {m.to && <span className="block text-muted-foreground">→ {AGENTS[m.to].name.replace(" Agent","")}</span>}
                </span>
                <p className="text-[13.5px] leading-snug">{m.text}</p>
              </li>
            ))}
          </ul>
        )}
      </Section>

      {/* Execution graph */}
      <Section title="Execution graph">
        <ExecutionGraph agents={focused?.agents.map(a => a.agentId) ?? []} />
      </Section>

      {/* Execution stream */}
      <Section title="Task execution stream">
        {!focused || focused.executionLog.length === 0 ? (
          <p className="text-sm text-muted-foreground italic">Stream idle.</p>
        ) : (
          <ul className="font-mono text-[12px] space-y-1.5 max-w-3xl">
            {focused.executionLog.map((l, i) => (
              <li key={i} className="flex gap-4 apa-fade-up">
                <span className="text-muted-foreground w-24 shrink-0">
                  {new Date(l.at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" })}
                </span>
                <span className="text-success">✓</span>
                <span className="text-muted-foreground w-24 shrink-0 uppercase tracking-wider text-[10px]">{l.agent}</span>
                <span>{l.label}</span>
              </li>
            ))}
          </ul>
        )}
      </Section>
    </Shell>
  );
}

function Dot({ s }: { s: AgentStatus }) {
  const cls =
    s === "running"  ? "bg-accent apa-pulse" :
    s === "thinking" ? "bg-accent/70 apa-pulse" :
    s === "queued"   ? "bg-muted-foreground/40" :
    s === "waiting"  ? "bg-warn" :
    s === "blocked"  ? "bg-destructive" :
    s === "done"     ? "bg-success" : "bg-muted-foreground/25";
  return <span className={`h-1.5 w-1.5 rounded-full ${cls}`} />;
}

function ExecutionGraph({ agents }: { agents: AgentId[] }) {
  if (agents.length === 0) {
    return <p className="text-sm text-muted-foreground italic">No execution graph yet.</p>;
  }
  const W = 800, H = 280;
  const top = "goal" as AgentId;
  const middle = agents.filter(a => a !== "goal");
  const cx = W / 2;
  return (
    <div className="rounded-xl border hairline bg-surface/40 overflow-hidden">
      <svg viewBox={`0 0 ${W} ${H}`} className="w-full h-auto">
        <Node x={cx} y={36} label="User outcome" sub="received" />
        <line x1={cx} y1={48} x2={cx} y2={86} stroke="var(--color-border-strong)" />
        <Node x={cx} y={108} label={AGENTS[top].name.replace(" Agent","")} sub="orchestrator" accent />
        {middle.map((a, i) => {
          const x = ((i + 1) / (middle.length + 1)) * W;
          const y = 200;
          return (
            <g key={a}>
              <line x1={cx} y1={120} x2={x} y2={y - 12} stroke="var(--color-border)" />
              <Node x={x} y={y} label={AGENTS[a].name.replace(" Agent","")} sub="executing" />
            </g>
          );
        })}
      </svg>
    </div>
  );
}
function Node({ x, y, label, sub, accent }: { x: number; y: number; label: string; sub: string; accent?: boolean }) {
  return (
    <g>
      <rect x={x - 70} y={y - 14} width="140" height="28" rx="6"
            fill="var(--color-background)"
            stroke={accent ? "var(--color-accent)" : "var(--color-border-strong)"} />
      <text x={x} y={y - 1} textAnchor="middle" fontFamily="var(--font-sans)"
            fontSize="11" fill="var(--color-foreground)">{label}</text>
      <text x={x} y={y + 10} textAnchor="middle" fontFamily="var(--font-mono)"
            fontSize="8" letterSpacing="1.4"
            fill="var(--color-muted-foreground)">{sub.toUpperCase()}</text>
    </g>
  );
}
