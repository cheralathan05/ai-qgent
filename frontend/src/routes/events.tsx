import { createFileRoute } from "@tanstack/react-router";
import { useMemo, useState } from "react";
import { Shell, PageHeader, Section } from "@/components/apa/Shell";
import { useApa } from "@/lib/apa/store";
import { useEnt } from "@/lib/apa/enterprise";

export const Route = createFileRoute("/events")({
  head: () => ({ meta: [{ title: "Live Events — APA-OS" }] }),
  component: EventsPage,
});

type EvtKind = "intent" | "device" | "execution" | "verification" | "memory" | "agent";

const KINDS: { id: EvtKind | "all"; label: string }[] = [
  { id: "all", label: "All" },
  { id: "intent", label: "Intent" },
  { id: "agent", label: "Agent" },
  { id: "memory", label: "Memory" },
  { id: "device", label: "Device" },
  { id: "execution", label: "Execution" },
  { id: "verification", label: "Verification" },
];

function EventsPage() {
  const outcomes = useApa(s => s.outcomes);
  const activity = useEnt(s => s.activity);
  const [filter, setFilter] = useState<EvtKind | "all">("all");
  const [paused, setPaused] = useState(false);

  const events = useMemo(() => {
    const out: { id: string; at: number; kind: EvtKind; title: string; meta: string; outcomeId?: string }[] = [];
    for (const o of outcomes) {
      out.push({ id: `${o.id}:intent`, at: o.createdAt, kind: "intent", title: `Intent detected · ${o.text}`, meta: o.category, outcomeId: o.id });
      for (const a of o.agents) {
        if (a.status === "done" || a.status === "running") {
          out.push({ id: `${o.id}:${a.agentId}`, at: o.createdAt + 100, kind: "agent", title: `${a.agentId} → ${a.status}`, meta: a.note ?? "", outcomeId: o.id });
        }
      }
      for (const l of o.executionLog) {
        const kind: EvtKind = l.label.toLowerCase().includes("verif") ? "verification" : "execution";
        out.push({ id: `${o.id}:${l.at}:${l.label}`, at: l.at, kind, title: l.label, meta: `${l.agent} · ${l.status}`, outcomeId: o.id });
      }
    }
    for (const a of activity) {
      const kind: EvtKind = a.kind === "command" ? "intent" : a.kind === "device" ? "device" : "execution";
      out.push({ id: a.id, at: a.at, kind, title: a.title, meta: a.kind });
    }
    return out.sort((x, y) => y.at - x.at);
  }, [outcomes, activity]);

  const filtered = events.filter(e => filter === "all" || e.kind === filter);

  return (
    <Shell>
      <PageHeader
        eyebrow="Phase 01 · Events"
        title="Live Event Feed."
        lede="Every signal — intent detected, device selected, execution started, verification passed or failed — streams here as the system thinks."
      />

      <div className="px-7 py-5 border-t hairline flex flex-wrap items-center gap-3">
        {KINDS.map(k => (
          <button key={k.id} onClick={() => setFilter(k.id)}
            className={`text-[11px] px-3 py-1.5 rounded-full border hairline transition
              ${filter === k.id ? "border-accent text-accent bg-accent/5" : "text-muted-foreground hover:text-foreground"}`}>
            {k.label}
          </button>
        ))}
        <span className="flex-1" />
        <button onClick={() => setPaused(p => !p)}
          className={`text-[10px] uppercase tracking-[0.22em] px-3 py-1.5 rounded border hairline
            ${paused ? "text-warn border-warn" : "text-muted-foreground"}`}>
          {paused ? "Paused" : "Live ●"}
        </button>
        <span className="font-mono text-[10px] text-muted-foreground">{filtered.length} events</span>
      </div>

      <div className="border-t hairline">
        {filtered.length === 0 ? (
          <div className="px-7 py-14 text-center">
            <p className="font-display text-[18px]">No events yet.</p>
            <p className="mt-2 text-[12px] text-muted-foreground">Run an outcome to see signals flow.</p>
          </div>
        ) : (
          <ul className={`divide-y hairline ${paused ? "opacity-60" : ""}`}>
            {filtered.slice(0, 80).map(e => (
              <li key={e.id} className="px-7 py-3.5 grid grid-cols-[110px_120px_1fr_auto] gap-5 items-baseline font-mono text-[11px]">
                <span className="text-muted-foreground">{new Date(e.at).toLocaleTimeString()}</span>
                <span className={`uppercase tracking-wider text-[9px] ${kindColor(e.kind)}`}>{e.kind}</span>
                <span className="font-sans text-[12.5px] text-foreground">{e.title}</span>
                <span className="text-muted-foreground text-[10px]">{e.meta}</span>
              </li>
            ))}
          </ul>
        )}
      </div>
    </Shell>
  );
}

function kindColor(k: string) {
  switch (k) {
    case "intent": return "text-accent";
    case "agent": return "text-accent/80";
    case "verification": return "text-[color:var(--color-success)]";
    case "execution": return "text-foreground";
    case "device": return "text-warn";
    case "memory": return "text-muted-foreground";
    default: return "text-muted-foreground";
  }
}
