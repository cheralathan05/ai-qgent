import { createFileRoute } from "@tanstack/react-router";
import { Shell, PageHeader, Section } from "@/components/apa/Shell";
import { useApa, apaStore } from "@/lib/apa/store";
import type { AutonomyMode } from "@/lib/apa/types";

export const Route = createFileRoute("/employee")({
  head: () => ({ meta: [{ title: "Employee Mode — APA-OS V3" }] }),
  component: EmployeePage,
});

const QUEUE = [
  { task: "Compile weekly placement report",          owner: "Research",      eta: "12 min", impact: "Goal · Placement" },
  { task: "Send Deepak the mock-test summary",        owner: "Communication", eta: "3 min",  impact: "Goal · Semester"  },
  { task: "Re-index Drive › College › Sem 5",          owner: "Memory",        eta: "8 min",  impact: "World model"      },
  { task: "Pre-stage VS Code workspace at 7:55 PM",   owner: "Device",        eta: "scheduled", impact: "Focus window"  },
  { task: "Run portal watcher · 5 min cadence",        owner: "Automation",    eta: "recurring", impact: "Risk radar"   },
];
const APPROVALS = [
  { task: "Send draft message to Deepak",       risk: "low",    why: "Outbound on your behalf"   },
  { task: "Update resume PDF on Drive",          risk: "medium", why: "Overwrites a file"         },
  { task: "Reschedule lab meet to 4:30 PM",      risk: "medium", why: "Notifies 4 people"         },
];

function EmployeePage() {
  const autonomy = useApa(s => s.autonomy);
  const modes: { id: AutonomyMode; label: string; desc: string }[] = [
    { id: "manual",     label: "Manual",     desc: "Suggest only. You execute every step." },
    { id: "assist",     label: "Assist",     desc: "Prepare actions. Ask before executing." },
    { id: "autonomous", label: "Autonomous", desc: "Execute approved playbooks automatically." },
  ];

  return (
    <Shell>
      <PageHeader
        eyebrow="Hidden Layer 20"
        title="Employee Mode."
        lede="Hand APA-OS a job description. It works the queue, asks for approval at risk gates, and reports back. Every action is logged and reversible."
      />

      <Section title="Autonomy contract">
        <ul className="grid grid-cols-1 md:grid-cols-3 gap-px bg-[var(--color-border)] border hairline">
          {modes.map(m => (
            <li key={m.id}>
              <button
                onClick={() => apaStore.set(s => ({ ...s, autonomy: m.id }))}
                className={[
                  "w-full text-left p-6 transition",
                  autonomy === m.id ? "bg-surface" : "bg-background hover:bg-surface/60",
                ].join(" ")}
              >
                <p className="font-mono text-[10px] uppercase tracking-[0.18em] text-accent">
                  {autonomy === m.id ? "active" : "available"}
                </p>
                <p className="mt-2 font-display text-2xl">{m.label}</p>
                <p className="mt-2 text-[12px] text-muted-foreground leading-relaxed">{m.desc}</p>
              </button>
            </li>
          ))}
        </ul>
      </Section>

      <Section title="Job description">
        <div className="max-w-3xl rounded-xl border hairline-strong bg-surface/60 p-5">
          <textarea
            rows={3}
            defaultValue={"Keep my semester goal on track. Watch the portal. Draft messages on my behalf. Refuse anything irreversible without my tap."}
            className="w-full bg-transparent text-[14px] outline-none resize-none placeholder:text-muted-foreground/50"
          />
          <div className="mt-3 flex items-center justify-between">
            <p className="font-mono text-[10px] uppercase tracking-wider text-muted-foreground">
              autonomy: <span className="text-accent">{autonomy}</span>
            </p>
            <button className="rounded-md bg-accent text-accent-foreground px-4 py-1.5 text-[12px]">Update contract</button>
          </div>
        </div>
      </Section>

      <Section title="Work queue">
        <ul className="grid grid-cols-1 md:grid-cols-2 gap-px bg-[var(--color-border)] border hairline">
          {QUEUE.map((q, i) => (
            <li key={i} className="bg-background p-5">
              <div className="flex items-baseline justify-between">
                <p className="text-[13.5px]">{q.task}</p>
                <span className="font-mono text-[10px] uppercase tracking-wider text-accent">{q.owner}</span>
              </div>
              <div className="mt-2 flex items-center justify-between font-mono text-[10px] text-muted-foreground uppercase tracking-wider">
                <span>{q.eta}</span>
                <span>{q.impact}</span>
              </div>
            </li>
          ))}
        </ul>
      </Section>

      <Section title="Awaiting approval">
        <ul className="space-y-3 max-w-3xl">
          {APPROVALS.map((a, i) => (
            <li key={i} className="flex items-center justify-between gap-6 border hairline rounded-lg p-4 bg-surface/40">
              <div>
                <p className="text-[13.5px]">{a.task}</p>
                <p className="mt-0.5 font-mono text-[10px] uppercase tracking-wider text-muted-foreground">
                  risk · <span className={a.risk === "low" ? "text-success" : "text-warn"}>{a.risk}</span> · {a.why}
                </p>
              </div>
              <div className="flex gap-2 shrink-0">
                <button className="rounded-md border hairline px-3 py-1.5 text-[12px] text-muted-foreground hover:text-foreground">Reject</button>
                <button className="rounded-md bg-accent text-accent-foreground px-3 py-1.5 text-[12px]">Approve</button>
              </div>
            </li>
          ))}
        </ul>
      </Section>
    </Shell>
  );
}
