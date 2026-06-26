import { createFileRoute } from "@tanstack/react-router";
import { useState } from "react";
import { Shell, PageHeader, Section } from "@/components/apa/Shell";
import { useApa } from "@/lib/apa/store";

export const Route = createFileRoute("/goals")({
  head: () => ({ meta: [{ title: "Goal Mission Center — APA-OS V3" }] }),
  component: GoalsPage,
});

const HEALTH = [
  { label: "Revision",    value: 78 },
  { label: "Assignments", value: 92 },
  { label: "Attendance",  value: 85 },
  { label: "Mock tests",  value: 34, tone: "warn" as const },
  { label: "Sleep",       value: 61 },
];

const SIM = [
  { label: "Current pace",        value: 47, note: "B+ likely" },
  { label: "+1 hr study daily",   value: 69, note: "A likely", tone: "success" as const },
  { label: "+2 mock tests / wk",  value: 84, note: "A confirmed", tone: "success" as const },
  { label: "No action",           value: 31, note: "C likely", tone: "warn" as const },
];
const RISKS = [
  { label: "Sleep deficit",   pct: 44, impact: "High"   },
  { label: "Missing mocks",   pct: 32, impact: "High"   },
  { label: "Pending DBMS",    pct: 18, impact: "Medium" },
];
const NEXT_ACTIONS = [
  { label: "Compilers Unit 4 revision", impact: "+3%", time: "45 min" },
  { label: "Approve resume draft",       impact: "+2%", time: "2 min" },
  { label: "Mock test (12 questions)",   impact: "+5%", time: "18 min" },
];

function GoalsPage() {
  const goals = useApa(s => s.goals);
  const [activeId, setActiveId] = useState(goals[0]?.id);
  const active = goals.find(g => g.id === activeId) ?? goals[0];

  return (
    <Shell>
      <PageHeader
        eyebrow="Hidden Layer 12 — the most important one"
        title="Goal Mission Center."
        lede="Goals don't sit on a page. They become the operating layer. What should I do right now to maximise my chance of achieving this?"
      />

      <Section title="North-stars">
        <ul className="grid grid-cols-1 md:grid-cols-2 gap-px bg-[var(--color-border)] border hairline">
          {goals.map(g => (
            <li key={g.id}>
              <button
                onClick={() => setActiveId(g.id)}
                className={[
                  "w-full text-left p-6 transition",
                  g.id === active?.id ? "bg-surface" : "bg-background hover:bg-surface/60",
                ].join(" ")}
              >
                <p className="text-[10px] uppercase tracking-[0.22em] text-accent">{g.horizon}</p>
                <p className="mt-2 font-display text-2xl tracking-tight">{g.title}</p>
                <div className="mt-4 flex items-baseline gap-3">
                  <span className="font-display text-4xl text-accent">{g.progress}<span className="text-xl text-muted-foreground">%</span></span>
                  <div className="flex-1 h-1 bg-[var(--color-border)] rounded">
                    <div className="h-full bg-accent" style={{ width: `${g.progress}%` }} />
                  </div>
                </div>
              </button>
            </li>
          ))}
        </ul>
      </Section>

      {active && (
        <>
          {/* Goal health */}
          <Section title={`${active.title} — health`}>
            <ul className="grid grid-cols-2 md:grid-cols-5 gap-px bg-[var(--color-border)] border hairline">
              {HEALTH.map(h => (
                <li key={h.label} className="bg-background p-5">
                  <p className="font-mono text-[10px] uppercase tracking-wider text-muted-foreground">{h.label}</p>
                  <p className={`mt-1.5 font-display text-3xl ${h.tone === "warn" ? "text-warn" : "text-foreground"}`}>{h.value}%</p>
                  <div className="mt-2 h-1 bg-[var(--color-border)] rounded">
                    <div className={`h-full ${h.tone === "warn" ? "bg-warn" : "bg-accent"}`} style={{ width: `${h.value}%` }} />
                  </div>
                </li>
              ))}
            </ul>
          </Section>

          {/* Next best action + Risks */}
          <Section>
            <div className="grid grid-cols-1 lg:grid-cols-[1.3fr_1fr] gap-px bg-[var(--color-border)] border hairline">
              <div className="bg-background p-6">
                <p className="text-[10px] uppercase tracking-[0.22em] text-accent">Next best action</p>
                <ul className="mt-4 space-y-3">
                  {NEXT_ACTIONS.map((a, i) => (
                    <li key={i} className="flex items-center justify-between gap-6 border-b hairline pb-3 last:border-0">
                      <div>
                        <p className="text-[14px]">{a.label}</p>
                        <p className="mt-0.5 font-mono text-[10px] uppercase tracking-wider text-muted-foreground">
                          impact {a.impact} · {a.time}
                        </p>
                      </div>
                      <button className="rounded-md border hairline-strong px-3 py-1.5 text-[12px] text-foreground hover:bg-accent hover:text-accent-foreground hover:border-accent transition">
                        Start now
                      </button>
                    </li>
                  ))}
                </ul>
              </div>

              <div className="bg-background p-6">
                <p className="text-[10px] uppercase tracking-[0.22em] text-warn">Risks detected</p>
                <ul className="mt-4 space-y-3">
                  {RISKS.map(r => (
                    <li key={r.label}>
                      <div className="flex items-baseline justify-between">
                        <span className="text-[13px]">{r.label}</span>
                        <span className="font-mono text-[10px] text-warn">{r.pct}%</span>
                      </div>
                      <div className="mt-1 h-[2px] bg-[var(--color-border)] rounded">
                        <div className="h-full bg-warn" style={{ width: `${r.pct}%` }} />
                      </div>
                      <p className="mt-1 font-mono text-[9.5px] uppercase tracking-wider text-muted-foreground">{r.impact}</p>
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          </Section>

          {/* Simulation */}
          <Section title="Future simulator" aside={
            <p className="font-mono text-[10px] uppercase tracking-wider text-muted-foreground">digital twin · world model</p>
          }>
            <ul className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-px bg-[var(--color-border)] border hairline">
              {SIM.map(s => (
                <li key={s.label} className="bg-background p-5">
                  <p className="font-mono text-[10px] uppercase tracking-wider text-muted-foreground">{s.label}</p>
                  <p className={`mt-2 font-display text-5xl ${
                    s.tone === "success" ? "text-success" : s.tone === "warn" ? "text-warn" : "text-accent"
                  }`}>{s.value}<span className="text-2xl text-muted-foreground">%</span></p>
                  <p className="mt-3 text-[12px] text-muted-foreground">{s.note}</p>
                </li>
              ))}
            </ul>
          </Section>

          {/* Agent team */}
          <Section title="Agent team on this goal">
            <ul className="flex flex-wrap gap-2">
              {["Goal — owner", "Planner — scheduling", "Learning — study plan", "Memory — weak topics", "Automation — reminders", "Communication — group pings"].map(t => (
                <li key={t} className="rounded-full border hairline px-3 py-1.5 text-[12px] text-muted-foreground">
                  {t}
                </li>
              ))}
            </ul>
          </Section>

          {/* Command */}
          <Section title="Re-plan in plain words">
            <div className="max-w-2xl rounded-xl border hairline-strong bg-surface/60 p-4">
              <input
                placeholder='"I only have 2 hours today" · "Move faster" · "Replan"'
                className="w-full bg-transparent text-[14px] outline-none placeholder:text-muted-foreground/50"
              />
              <p className="mt-2 font-mono text-[10px] uppercase tracking-wider text-muted-foreground">
                ↵ to re-run goal orchestrator
              </p>
            </div>
          </Section>
        </>
      )}
    </Shell>
  );
}
