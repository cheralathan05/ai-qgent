import { createFileRoute } from "@tanstack/react-router";
import { Shell, PageHeader, Section } from "@/components/apa/Shell";

export const Route = createFileRoute("/projects")({
  head: () => ({ meta: [{ title: "Projects — APA-OS" }] }),
  component: ProjectsPage,
});

const PROJECTS = [
  { name: "ATM Protocol",  repo: "github.com/cher/atm", progress: 64, tasks: 12, open: 4 },
  { name: "Eyesona",        repo: "github.com/cher/eyesona", progress: 41, tasks: 22, open: 9 },
  { name: "APA-OS frontend",repo: "github.com/cher/apa-os", progress: 78, tasks: 38, open: 6 },
];

function ProjectsPage() {
  return (
    <Shell>
      <PageHeader
        eyebrow="Phase 04 · Projects"
        title="Projects."
        lede="What you're actually building — progress, architecture, open tasks. The real work, tracked."
      />

      <Section title={`Active · ${PROJECTS.length}`}>
        <ul className="space-y-3">
          {PROJECTS.map(p => (
            <li key={p.name} className="border hairline rounded-md p-5">
              <div className="flex items-baseline justify-between">
                <div>
                  <p className="font-display text-[18px]">{p.name}</p>
                  <p className="mt-0.5 text-[10px] uppercase tracking-wider text-muted-foreground">{p.repo}</p>
                </div>
                <span className="font-mono text-[11px] text-accent">{p.progress}%</span>
              </div>
              <div className="mt-3 h-[2px] bg-[var(--color-border)] rounded"><div className="h-full bg-accent" style={{ width: `${p.progress}%` }} /></div>
              <p className="mt-3 text-[11px] text-muted-foreground">{p.tasks} tasks · {p.open} open</p>
            </li>
          ))}
        </ul>
      </Section>
    </Shell>
  );
}
