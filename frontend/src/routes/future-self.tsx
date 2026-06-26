import { createFileRoute } from "@tanstack/react-router";
import { Shell, PageHeader, Section } from "@/components/apa/Shell";

export const Route = createFileRoute("/future-self")({
  head: () => ({ meta: [{ title: "Future Self — APA-OS" }] }),
  component: FutureSelfPage,
});

const PILLARS = [
  { label: "Technical depth", current: 64, target: 88 },
  { label: "System design",   current: 42, target: 82 },
  { label: "Shipping cadence",current: 51, target: 80 },
  { label: "Writing",          current: 35, target: 70 },
  { label: "Health · sleep",   current: 58, target: 78 },
];

function FutureSelfPage() {
  return (
    <Shell>
      <PageHeader
        eyebrow="Phase 04 · Future Self"
        title="Future Self."
        lede="The version of you APA is helping you become. Current state · target state · honest gap."
      />

      <Section title="Trajectory">
        <ul className="space-y-4">
          {PILLARS.map(p => {
            const gap = p.target - p.current;
            return (
              <li key={p.label}>
                <div className="flex items-baseline justify-between">
                  <span className="text-[13px]">{p.label}</span>
                  <span className="font-mono text-[10px] text-muted-foreground">
                    {p.current}% → <span className="text-accent">{p.target}%</span> · +{gap}
                  </span>
                </div>
                <div className="mt-2 h-[3px] bg-[var(--color-border)] rounded overflow-hidden relative">
                  <div className="absolute inset-y-0 left-0 bg-accent/30" style={{ width: `${p.target}%` }} />
                  <div className="absolute inset-y-0 left-0 bg-accent" style={{ width: `${p.current}%` }} />
                </div>
              </li>
            );
          })}
        </ul>
      </Section>

      <Section title="Gap analysis">
        <p className="text-[13px] text-muted-foreground leading-relaxed max-w-2xl">
          The largest deltas are <span className="text-accent">system design</span> and <span className="text-accent">writing</span>.
          A daily 45-minute sprint on each — held in your 8–10 PM focus window — would close 60% of the gap by exam season.
        </p>
      </Section>
    </Shell>
  );
}
