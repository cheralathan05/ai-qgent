import { createFileRoute } from "@tanstack/react-router";
import { Shell, PageHeader, Section } from "@/components/apa/Shell";

export const Route = createFileRoute("/reality")({
  head: () => ({ meta: [{ title: "Reality Check — APA-OS" }] }),
  component: RealityPage,
});

const USAGE = [
  { label: "Focused work",  pct: 22, tone: "ok" },
  { label: "Learning",       pct: 14, tone: "ok" },
  { label: "Social / scroll",pct: 31, tone: "warn" },
  { label: "Communication",  pct: 12, tone: "ok" },
  { label: "Idle / sleep",   pct: 21, tone: "ok" },
];

const RECS = [
  "Social time is 31% of waking hours. Cap Instagram at 45 min/day to free 6h/week.",
  "Focus blocks miss target by ~40 min. Pull them earlier — 7:30 PM instead of 8 PM.",
  "Two evenings drift past 1 AM. Sleep debt hurts derivation speed the most.",
];

function RealityPage() {
  return (
    <Shell>
      <PageHeader
        eyebrow="Phase 04 · Reality"
        title="Reality Check."
        lede="Where the time actually goes. Where intent met execution — and where it didn't."
      />

      <Section title="Time usage (last 7 days)">
        <ul className="space-y-3">
          {USAGE.map(u => (
            <li key={u.label}>
              <div className="flex justify-between text-[12px]">
                <span>{u.label}</span>
                <span className={`font-mono text-[10px] ${u.tone === "warn" ? "text-warn" : "text-muted-foreground"}`}>{u.pct}%</span>
              </div>
              <div className="mt-1 h-[2px] bg-[var(--color-border)] rounded">
                <div className={`h-full ${u.tone === "warn" ? "bg-warn" : "bg-accent"}`} style={{ width: `${u.pct * 2.5}%` }} />
              </div>
            </li>
          ))}
        </ul>
      </Section>

      <Section title="Alignment score">
        <p className="font-display text-[44px] text-accent leading-none">62<span className="text-[20px] text-muted-foreground">/100</span></p>
        <p className="mt-2 text-[12px] text-muted-foreground">Actions vs stated goals. Improving — up 8 points this week.</p>
      </Section>

      <Section title="Recommendations">
        <ul className="space-y-2">
          {RECS.map((r, i) => <li key={i} className="text-[13px] leading-relaxed">— {r}</li>)}
        </ul>
      </Section>
    </Shell>
  );
}
