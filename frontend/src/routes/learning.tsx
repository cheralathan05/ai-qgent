import { createFileRoute } from "@tanstack/react-router";
import { Shell, PageHeader, Section } from "@/components/apa/Shell";

export const Route = createFileRoute("/learning")({
  head: () => ({ meta: [{ title: "Learning — APA-OS" }] }),
  component: LearningPage,
});

const TRACKS = [
  { kind: "Course",   title: "Designing Data-Intensive Applications", progress: 38 },
  { kind: "Video",    title: "MIT 6.824 — Distributed Systems",       progress: 22 },
  { kind: "Book",     title: "Crafting Interpreters",                  progress: 61 },
  { kind: "Project",  title: "ATM Protocol v2 — reliability layer",   progress: 47 },
  { kind: "Roadmap",  title: "Backend engineer · 6 months",           progress: 28 },
];

function LearningPage() {
  return (
    <Shell>
      <PageHeader
        eyebrow="Phase 04 · Learning"
        title="Learning."
        lede="Courses, books, projects, roadmaps — sequenced into a single learning curve."
      />

      <Section title={`Active tracks · ${TRACKS.length}`}>
        <ul className="space-y-3">
          {TRACKS.map(t => (
            <li key={t.title} className="border hairline rounded-md p-4">
              <div className="flex items-baseline justify-between">
                <p className="font-display text-[15px]">{t.title}</p>
                <span className="font-mono text-[10px] text-accent">{t.progress}%</span>
              </div>
              <p className="mt-0.5 text-[10px] uppercase tracking-wider text-muted-foreground">{t.kind}</p>
              <div className="mt-2 h-[2px] bg-[var(--color-border)] rounded"><div className="h-full bg-accent" style={{ width: `${t.progress}%` }} /></div>
            </li>
          ))}
        </ul>
      </Section>
    </Shell>
  );
}
