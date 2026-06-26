import { createFileRoute, Link } from "@tanstack/react-router";
import { Shell, PageHeader, Section } from "@/components/apa/Shell";
import { useApa } from "@/lib/apa/store";

export const Route = createFileRoute("/life")({
  head: () => ({ meta: [{ title: "Life — APA-OS" }] }),
  component: LifePage,
});

function LifePage() {
  const goals = useApa(s => s.goals);

  return (
    <Shell>
      <PageHeader
        eyebrow="Phase 04 · Life Intelligence"
        title="Life."
        lede="Future self, goals, career, learning — the long-horizon model of you. Slow, important, honest."
      />

      <Section title="Long horizons">
        <ul className="grid sm:grid-cols-2 gap-3">
          {[
            { to: "/future-self", label: "Future Self", hint: "Current → target" },
            { to: "/goals", label: "Goals", hint: "North stars" },
            { to: "/career", label: "Career", hint: "Readiness" },
            { to: "/learning", label: "Learning", hint: "Sprints" },
            { to: "/projects", label: "Projects", hint: "What you ship" },
            { to: "/reality", label: "Reality Check", hint: "Where the time goes" },
          ].map(it => (
            <li key={it.to}>
              <Link to={it.to} className="block border hairline rounded-md p-5 hover:border-accent transition">
                <p className="text-[9px] uppercase tracking-[0.22em] text-accent">{it.hint}</p>
                <p className="mt-1 font-display text-[18px]">{it.label}</p>
              </Link>
            </li>
          ))}
        </ul>
      </Section>

      <Section title="Active goals">
        <ul className="divide-y hairline">
          {goals.map(g => (
            <li key={g.id} className="py-3 grid grid-cols-[1fr_120px_60px] gap-4 items-baseline">
              <span className="text-[13px]">{g.title}</span>
              <span className="text-[10px] uppercase tracking-wider text-muted-foreground">{g.horizon}</span>
              <span className="font-mono text-[11px] text-accent text-right">{g.progress}%</span>
            </li>
          ))}
        </ul>
      </Section>
    </Shell>
  );
}
