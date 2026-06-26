import { createFileRoute } from "@tanstack/react-router";
import { Shell, PageHeader, Section } from "@/components/apa/Shell";

export const Route = createFileRoute("/predictions")({
  head: () => ({ meta: [{ title: "Prediction Engine — APA-OS V2" }] }),
  component: PredictionsPage,
});

const PREDICTIONS = [
  { label: "Exam readiness",        value: 74, tone: "ok",   detail: "Compilers Unit 4 weakest — 3 sessions away from green." },
  { label: "Placement readiness",   value: 61, tone: "ok",   detail: "Resume gap on system design projects." },
  { label: "Burnout risk",          value: 68, tone: "warn", detail: "Sleep window slipped 3 nights in a row." },
  { label: "On-time submission",    value: 91, tone: "good", detail: "All pending assignments on trajectory." },
  { label: "Goal trajectory",       value: 57, tone: "ok",   detail: "Semester on track. Placement behind plan by 2 weeks." },
  { label: "Surprise event risk",   value: 22, tone: "good", detail: "College portal & inbox quiet for the last 36 hours." },
];

function tone(t: string) {
  return t === "good" ? "var(--color-success)"
       : t === "warn" ? "var(--color-warn)"
       : "var(--color-accent)";
}

function PredictionsPage() {
  return (
    <Shell>
      <PageHeader
        eyebrow="Hidden Layer 05"
        title="Prediction Engine."
        lede="What is likely to be true tomorrow, next week, next month — given your habits, your deadlines, and what the world is doing around you."
      />
      <Section>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-px bg-[var(--color-border)] border hairline">
          {PREDICTIONS.map(p => (
            <div key={p.label} className="bg-background p-7">
              <p className="font-mono text-[10px] uppercase tracking-[0.18em] text-muted-foreground">{p.label}</p>
              <p className="mt-3 font-display text-5xl tracking-tight" style={{ color: tone(p.tone) }}>
                {p.value}<span className="text-2xl text-muted-foreground">%</span>
              </p>
              <div className="mt-3 h-[3px] w-full bg-[var(--color-border)] rounded-full overflow-hidden">
                <div className="h-full" style={{ width: `${p.value}%`, background: tone(p.tone) }} />
              </div>
              <p className="mt-4 text-[12px] text-muted-foreground leading-relaxed">{p.detail}</p>
            </div>
          ))}
        </div>
      </Section>
    </Shell>
  );
}
