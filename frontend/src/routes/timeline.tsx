import { createFileRoute } from "@tanstack/react-router";
import { useState, useMemo } from "react";
import { Shell, PageHeader, Section } from "@/components/apa/Shell";
import { useEnt } from "@/lib/apa/enterprise";
import type { ActivityKind } from "@/lib/apa/enterprise";

export const Route = createFileRoute("/timeline")({
  head: () => ({ meta: [{ title: "Activity Timeline — APA-OS" }] }),
  component: TimelinePage,
});

const KINDS: ActivityKind[] = ["command","device","knowledge","file","workflow","approval","notification","error","user","execution"];

function TimelinePage() {
  const activity = useEnt(s => s.activity);
  const [q, setQ] = useState("");
  const [active, setActive] = useState<Set<ActivityKind>>(new Set(KINDS));

  const items = useMemo(() => activity.filter(a =>
    active.has(a.kind) && (!q || a.title.toLowerCase().includes(q.toLowerCase()))
  ), [activity, active, q]);

  function toggle(k: ActivityKind) {
    setActive(prev => {
      const next = new Set(prev);
      next.has(k) ? next.delete(k) : next.add(k);
      return next;
    });
  }

  return (
    <Shell>
      <PageHeader eyebrow="Hidden Layer 04" title="Unified Activity Timeline."
        lede="Commands, device actions, knowledge searches, file access, workflow runs, approvals, notifications, errors — one chronological stream." />
      <Section>
        <div className="flex flex-wrap items-center gap-2 mb-6">
          <input value={q} onChange={e => setQ(e.target.value)} placeholder="Filter activity…"
            className="bg-surface rounded-md px-3 py-1.5 text-[12px] border hairline focus:border-accent outline-none w-64" />
          {KINDS.map(k => (
            <button key={k} onClick={() => toggle(k)}
              className={["px-2.5 py-1 rounded-md text-[10px] uppercase tracking-[0.18em] border hairline",
                active.has(k) ? "bg-accent text-accent-foreground border-transparent" : "text-muted-foreground hover:text-foreground"].join(" ")}>{k}</button>
          ))}
        </div>

        <ul className="relative pl-6 border-l hairline-strong">
          {items.map(a => (
            <li key={a.id} className="relative py-3">
              <span className="absolute -left-[7px] top-5 h-2.5 w-2.5 rounded-full bg-accent" />
              <div className="flex items-baseline justify-between gap-4">
                <p className="text-[13px]">{a.title}</p>
                <span className="font-mono text-[10px] text-muted-foreground shrink-0">{new Date(a.at).toLocaleString()}</span>
              </div>
              <p className="mt-0.5 font-mono text-[10px] uppercase tracking-wider text-accent">{a.kind}{a.source ? ` · ${a.source}` : ""}</p>
            </li>
          ))}
          {items.length === 0 && <li className="py-10 text-center text-muted-foreground italic text-[12px]">No matching activity.</li>}
        </ul>
      </Section>
    </Shell>
  );
}
