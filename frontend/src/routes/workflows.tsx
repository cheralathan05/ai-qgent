import { createFileRoute } from "@tanstack/react-router";
import { useState } from "react";
import { Shell, PageHeader, Section } from "@/components/apa/Shell";
import { useApa } from "@/lib/apa/store";
import { runOutcome } from "@/lib/apa/orchestrator";

export const Route = createFileRoute("/workflows")({
  head: () => ({ meta: [{ title: "Workflows — APA-OS" }] }),
  component: WorkflowsPage,
});

function WorkflowsPage() {
  const outcomes = useApa(s => s.outcomes);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const selected = outcomes.find(o => o.id === selectedId) ?? outcomes[0];

  return (
    <Shell>
      <PageHeader
        eyebrow="Phase 01 · Workflows"
        title="Workflow Center."
        lede="Every outcome becomes a workflow — agents, steps, timeline, verification. Watch them run, retry, or replay."
      />

      <div className="grid lg:grid-cols-[340px_1fr] gap-0 border-t hairline">
        <aside className="border-r hairline px-6 py-6 max-h-[80vh] overflow-y-auto">
          <p className="text-[9px] uppercase tracking-[0.22em] text-muted-foreground mb-4">{outcomes.length} workflows</p>
          {outcomes.length === 0 ? (
            <p className="text-[12px] text-muted-foreground italic">No workflows yet. Start an outcome from the Console or Assistant.</p>
          ) : (
            <ul className="space-y-2">
              {outcomes.map(o => {
                const active = selected?.id === o.id;
                const done = o.agents.filter(a => a.status === "done").length;
                return (
                  <li key={o.id}>
                    <button onClick={() => setSelectedId(o.id)}
                      className={`w-full text-left rounded-md px-3 py-2.5 border hairline transition
                        ${active ? "bg-surface border-[color:var(--color-border-strong)]" : "hover:bg-surface/60"}`}>
                      <p className="text-[12.5px] leading-snug line-clamp-2">{o.text}</p>
                      <p className="mt-1.5 flex items-center gap-2 text-[10px] text-muted-foreground">
                        <span className={`h-1 w-1 rounded-full ${o.currentStage === "complete" ? "bg-[color:var(--color-success)]" : "bg-accent apa-pulse"}`} />
                        {o.currentStage} · {done}/{o.agents.length} agents
                      </p>
                    </button>
                  </li>
                );
              })}
            </ul>
          )}
        </aside>

        <div className="min-h-[60vh]">
          {selected ? <WorkflowDetail outcome={selected} /> : (
            <div className="px-7 py-14 text-center">
              <p className="font-display text-[18px]">Select a workflow.</p>
            </div>
          )}
        </div>
      </div>
    </Shell>
  );
}

function WorkflowDetail({ outcome }: { outcome: ReturnType<typeof useApa<any>> extends infer T ? any : never }) {
  const o = outcome;
  return (
    <div className="px-7 py-7 space-y-7">
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="text-[9px] uppercase tracking-[0.22em] text-accent">{o.category}</p>
          <h2 className="mt-1 font-display text-[28px] leading-tight">{o.text}</h2>
          <p className="mt-2 text-[12px] text-muted-foreground">
            Started {new Date(o.createdAt).toLocaleTimeString()} · {o.duration} · priority {o.priority}
          </p>
        </div>
        <div className="flex gap-2 text-[10px] uppercase tracking-[0.22em]">
          <button onClick={() => runOutcome(o.text)}
            className="px-3 py-1.5 border hairline rounded text-muted-foreground hover:text-accent hover:border-accent">
            Retry
          </button>
        </div>
      </div>

      <Stages stage={o.currentStage} />

      <div className="grid lg:grid-cols-2 gap-7">
        <Block title="Agents">
          <ul className="space-y-2">
            {o.agents.map((a: any) => (
              <li key={a.agentId} className="flex items-center justify-between text-[12px]">
                <span className="flex items-center gap-2">
                  <span className={`h-1.5 w-1.5 rounded-full ${a.status === "done" ? "bg-[color:var(--color-success)]" : a.status === "running" || a.status === "thinking" ? "bg-accent apa-pulse" : "bg-muted-foreground/30"}`} />
                  <span>{a.agentId}</span>
                </span>
                <span className="font-mono text-[9px] uppercase tracking-wider text-muted-foreground">
                  {a.status}{a.confidence ? ` · ${a.confidence}%` : ""}
                </span>
              </li>
            ))}
          </ul>
        </Block>

        <Block title="Verification">
          <ul className="space-y-2 font-mono text-[11px]">
            {o.executionLog.map((l: any, i: number) => (
              <li key={i} className="flex gap-3">
                <span className="text-muted-foreground">{new Date(l.at).toLocaleTimeString()}</span>
                <span className={l.status === "ok" ? "text-[color:var(--color-success)]" : l.status === "warn" ? "text-warn" : "text-accent"}>[{l.status}]</span>
                <span className="flex-1">{l.label}</span>
              </li>
            ))}
            {o.executionLog.length === 0 && <li className="text-muted-foreground italic">Awaiting verification…</li>}
          </ul>
        </Block>
      </div>

      <Block title="Steps">
        <ol className="space-y-3">
          {o.plan.map((s: any, i: number) => (
            <li key={s.id} className="grid grid-cols-[24px_1fr_140px] gap-3 items-baseline">
              <span className="font-mono text-[10px] text-muted-foreground">{String(i + 1).padStart(2, "0")}</span>
              <div>
                <p className="text-[13px]">{s.title}</p>
                <p className="mt-0.5 text-[11px] text-muted-foreground">{s.detail}</p>
              </div>
              <span className="text-[10px] uppercase tracking-wider text-muted-foreground text-right">{s.when}</span>
            </li>
          ))}
        </ol>
      </Block>
    </div>
  );
}

function Stages({ stage }: { stage: string }) {
  const stages = ["intent","agents","memory","world","predictions","plan","execution","complete"];
  const idx = stages.indexOf(stage);
  return (
    <div>
      <div className="flex gap-1">
        {stages.map((s, i) => (
          <div key={s} className="flex-1">
            <div className={`h-[2px] rounded ${i <= idx ? "bg-accent" : "bg-[var(--color-border)]"}`} />
            <p className={`mt-1.5 text-[9px] uppercase tracking-[0.18em] ${i === idx ? "text-accent" : "text-muted-foreground"}`}>{s}</p>
          </div>
        ))}
      </div>
    </div>
  );
}

function Block({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div>
      <p className="text-[9px] uppercase tracking-[0.22em] text-muted-foreground mb-3">{title}</p>
      {children}
    </div>
  );
}
