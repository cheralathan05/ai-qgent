import { createFileRoute } from "@tanstack/react-router";
import { Shell, PageHeader, Section } from "@/components/apa/Shell";

export const Route = createFileRoute("/research")({
  head: () => ({ meta: [{ title: "Research — APA-OS" }] }),
  component: ResearchPage,
});

const TASKS = [
  { id: "r1", title: "Top 12 product startups hiring backend interns Q1", status: "complete", insights: 7 },
  { id: "r2", title: "State of RAG over personal knowledge — 2026",        status: "running",  insights: 3 },
  { id: "r3", title: "Compare React 19 vs Solid Start for AI-first UIs",   status: "queued",   insights: 0 },
];

function ResearchPage() {
  return (
    <Shell>
      <PageHeader
        eyebrow="Phase 05 · Research"
        title="Research."
        lede="Long-running investigations the Research Agent runs in the background. Reports, summaries, insights — surfaced when ready."
      />

      <Section title={`Active · ${TASKS.length}`}>
        <ul className="space-y-3">
          {TASKS.map(t => (
            <li key={t.id} className="border hairline rounded-md p-5">
              <div className="flex items-baseline justify-between">
                <p className="font-display text-[15px]">{t.title}</p>
                <span className={`text-[10px] uppercase tracking-[0.22em] ${t.status === "complete" ? "text-[color:var(--color-success)]" : t.status === "running" ? "text-accent" : "text-muted-foreground"}`}>
                  {t.status}
                </span>
              </div>
              <p className="mt-1 text-[11px] text-muted-foreground">{t.insights} insights extracted</p>
            </li>
          ))}
        </ul>
      </Section>
    </Shell>
  );
}
