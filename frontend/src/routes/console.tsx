import { createFileRoute } from "@tanstack/react-router";
import { useMemo, useState } from "react";
import { Shell, PageHeader, Section } from "@/components/apa/Shell";
import { useApa } from "@/lib/apa/store";
import { runOutcome } from "@/lib/apa/orchestrator";
import { pushActivity, useEnt } from "@/lib/apa/enterprise";

export const Route = createFileRoute("/console")({
  head: () => ({ meta: [{ title: "Command Console — APA-OS" }] }),
  component: ConsolePage,
});

const SUGGESTIONS = [
  "Open Instagram",
  "Open WhatsApp",
  "Open Chrome",
  "Open Settings",
  "Take Screenshot",
  "Get Battery",
  "Help me prepare for tomorrow",
  "Send the attendance screenshot to Deepak",
];

function ConsolePage() {
  const [q, setQ] = useState("");
  const outcomes = useApa(s => s.outcomes);
  const activity = useEnt(s => s.activity);
  const focused = outcomes[0];

  const filtered = useMemo(() => {
    if (!q) return SUGGESTIONS;
    return SUGGESTIONS.filter(s => s.toLowerCase().includes(q.toLowerCase()));
  }, [q]);

  async function run(text: string) {
    if (!text.trim()) return;
    pushActivity({ kind: "command", title: `Console · ${text}` });
    setQ("");
    await runOutcome(text);
  }

  return (
    <Shell>
      <PageHeader
        eyebrow="Phase 01 · Console"
        title="Command Console."
        lede="Type any outcome. Watch the agent floor, execution timeline, and verification stream in real time."
      />

      <div className="px-7 py-7 border-t hairline">
        <form onSubmit={e => { e.preventDefault(); void run(q); }}
          className="flex items-center gap-3 bg-surface border hairline-strong rounded-lg px-5 py-4">
          <span className="font-mono text-[10px] uppercase tracking-[0.22em] text-accent">{">"}</span>
          <input
            autoFocus
            className="flex-1 bg-transparent outline-none text-[15px] placeholder:text-muted-foreground/50"
            placeholder="Open Instagram · Take a screenshot · Help me prepare for tomorrow…"
            value={q}
            onChange={e => setQ(e.target.value)}
          />
          <button className="text-[10px] uppercase tracking-[0.22em] text-accent hover:opacity-80">Run ↵</button>
        </form>

        <div className="mt-3 flex flex-wrap gap-2">
          {filtered.map(s => (
            <button key={s} onClick={() => run(s)}
              className="text-[11px] px-3 py-1.5 rounded-full border hairline text-muted-foreground hover:text-foreground hover:border-[color:var(--color-border-strong)] transition">
              {s}
            </button>
          ))}
        </div>
      </div>

      <Section title="Execution timeline" aside={
        <p className="font-mono text-[10px] uppercase tracking-wider text-muted-foreground">{outcomes.length} runs</p>
      }>
        {outcomes.length === 0 ? (
          <Empty />
        ) : (
          <ul className="divide-y hairline">
            {outcomes.map(o => (
              <li key={o.id} className="py-4 grid grid-cols-[160px_1fr_120px] gap-5 items-baseline">
                <span className="font-mono text-[10px] uppercase tracking-wider text-muted-foreground">
                  {new Date(o.createdAt).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                </span>
                <div>
                  <p className="font-display text-[15px] leading-snug">{o.text}</p>
                  <p className="mt-1 text-[10.5px] text-muted-foreground">
                    {o.category} · {o.agents.filter(a => a.status === "done").length}/{o.agents.length} agents · stage {o.currentStage}
                  </p>
                  <div className="mt-2 h-[2px] bg-[var(--color-border)] rounded">
                    <div className="h-full bg-accent transition-all" style={{ width: `${stagePct(o.currentStage)}%` }} />
                  </div>
                </div>
                <div className="flex justify-end gap-3 text-[10px] uppercase tracking-[0.22em]">
                  <button onClick={() => runOutcome(o.text)} className="text-muted-foreground hover:text-accent">Retry</button>
                </div>
              </li>
            ))}
          </ul>
        )}
      </Section>

      {focused && (
        <Section title="Live workflow" aside={<span className="font-mono text-[10px] uppercase tracking-wider text-accent">{focused.currentStage}</span>}>
          <div className="grid lg:grid-cols-2 gap-6">
            <div>
              <p className="text-[9px] uppercase tracking-[0.22em] text-muted-foreground mb-3">Plan</p>
              <ol className="space-y-2">
                {focused.plan.map((p, i) => (
                  <li key={p.id} className="flex gap-3 text-[12.5px]">
                    <span className="font-mono text-[10px] text-muted-foreground w-5">{String(i + 1).padStart(2, "0")}</span>
                    <div className="flex-1">
                      <p>{p.title}</p>
                      <p className="text-[10.5px] text-muted-foreground mt-0.5">{p.detail}</p>
                    </div>
                    <span className="text-[9px] uppercase tracking-wider text-muted-foreground">{p.when}</span>
                  </li>
                ))}
              </ol>
            </div>
            <div>
              <p className="text-[9px] uppercase tracking-[0.22em] text-muted-foreground mb-3">Execution log</p>
              <ul className="space-y-1.5 font-mono text-[11px]">
                {focused.executionLog.map((l, i) => (
                  <li key={i} className="flex gap-3">
                    <span className="text-muted-foreground">{new Date(l.at).toLocaleTimeString()}</span>
                    <span className={l.status === "ok" ? "text-[color:var(--color-success)]" : l.status === "warn" ? "text-warn" : "text-accent"}>
                      [{l.status}]
                    </span>
                    <span className="flex-1">{l.label}</span>
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </Section>
      )}

      <Section title="Recent activity">
        <ul className="space-y-1.5 font-mono text-[11px]">
          {activity.slice(0, 12).map(a => (
            <li key={a.id} className="flex gap-3 text-muted-foreground">
              <span>{new Date(a.at).toLocaleTimeString()}</span>
              <span className="text-accent uppercase tracking-wider text-[9px]">{a.kind}</span>
              <span className="flex-1 text-foreground">{a.title}</span>
            </li>
          ))}
        </ul>
      </Section>
    </Shell>
  );
}

function stagePct(s: string) {
  const order = ["intent","agents","memory","world","predictions","plan","execution","complete"];
  return ((order.indexOf(s) + 1) / order.length) * 100;
}

function Empty() {
  return (
    <div className="py-14 text-center">
      <p className="font-display text-[18px]">No commands yet.</p>
      <p className="mt-2 text-[12px] text-muted-foreground">Type above or pick a suggestion. The system stays quiet until you speak.</p>
    </div>
  );
}
