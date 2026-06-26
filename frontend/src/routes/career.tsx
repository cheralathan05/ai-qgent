import { createFileRoute } from "@tanstack/react-router";
import { Shell, PageHeader, Section } from "@/components/apa/Shell";

export const Route = createFileRoute("/career")({
  head: () => ({ meta: [{ title: "Career — APA-OS" }] }),
  component: CareerPage,
});

const SKILLS = [
  { name: "DSA", level: 72 }, { name: "System design", level: 42 },
  { name: "TypeScript", level: 86 }, { name: "Python", level: 74 },
  { name: "Networking", level: 61 }, { name: "Databases", level: 68 },
];
const READINESS = [
  { label: "Internship readiness", value: 71 },
  { label: "Job readiness",        value: 58 },
  { label: "Resume quality",       value: 82 },
];
const RECS = [
  "Add ATM Protocol metrics to resume — concrete numbers beat adjectives.",
  "Two system-design mocks per week for 4 weeks closes the largest gap.",
  "Apply to 3 product companies from the shortlist this Friday.",
];

function CareerPage() {
  return (
    <Shell>
      <PageHeader
        eyebrow="Phase 04 · Career"
        title="Career."
        lede="What you're ready for today, what's close, what isn't. And what to do about it this week."
      />

      <Section title="Readiness">
        <ul className="grid sm:grid-cols-3 gap-5">
          {READINESS.map(r => (
            <li key={r.label}>
              <p className="text-[9px] uppercase tracking-[0.22em] text-muted-foreground">{r.label}</p>
              <p className="mt-2 font-display text-[28px] text-accent">{r.value}%</p>
              <div className="mt-2 h-[2px] bg-[var(--color-border)] rounded"><div className="h-full bg-accent" style={{ width: `${r.value}%` }} /></div>
            </li>
          ))}
        </ul>
      </Section>

      <Section title="Skills">
        <ul className="grid sm:grid-cols-2 gap-3">
          {SKILLS.map(s => (
            <li key={s.name}>
              <div className="flex justify-between text-[12px]"><span>{s.name}</span><span className="font-mono text-[10px] text-muted-foreground">{s.level}%</span></div>
              <div className="mt-1 h-[2px] bg-[var(--color-border)] rounded"><div className="h-full bg-accent" style={{ width: `${s.level}%` }} /></div>
            </li>
          ))}
        </ul>
      </Section>

      <Section title="Recommendations">
        <ul className="space-y-2">
          {RECS.map((r, i) => <li key={i} className="text-[13px] text-foreground/90 leading-relaxed">— {r}</li>)}
        </ul>
      </Section>
    </Shell>
  );
}
