import { createFileRoute, Link } from "@tanstack/react-router";
import { Shell, PageHeader, Section } from "@/components/apa/Shell";
import { entStore, useEnt } from "@/lib/apa/enterprise";

export const Route = createFileRoute("/onboarding")({
  head: () => ({ meta: [{ title: "Welcome — APA-OS" }] }),
  component: OnboardingPage,
});

const STEPS = [
  { title: "Create your account",     detail: "You're in. Identity established, workspace seeded." },
  { title: "Connect your first device", detail: "Phone, laptop, browser — APA-OS observes before it acts." },
  { title: "Connect knowledge",       detail: "Drive, notes, files. The Memory Agent will index quietly." },
  { title: "Grant permissions",       detail: "Choose what APA-OS may see and what it must ask before doing." },
  { title: "Run your first outcome",  detail: "Say what you want. The orchestrator does the rest." },
];

function OnboardingPage() {
  const done = useEnt(s => s.onboardingComplete);
  return (
    <Shell>
      <PageHeader eyebrow="Welcome" title="Set up APA-OS."
        lede="Five quiet steps. After this, you stop opening apps." />
      <Section>
        <ol className="space-y-3">
          {STEPS.map((s, i) => (
            <li key={s.title} className="flex gap-5 border hairline rounded-md p-5">
              <span className="font-display text-3xl text-accent w-10 shrink-0">{String(i+1).padStart(2,"0")}</span>
              <div className="flex-1">
                <p className="font-display text-[18px]">{s.title}</p>
                <p className="mt-1 text-[12.5px] text-muted-foreground">{s.detail}</p>
              </div>
              <span className="font-mono text-[10px] uppercase tracking-wider text-[color:var(--color-success)] self-center">done</span>
            </li>
          ))}
        </ol>
        <div className="mt-8 flex items-center gap-3">
          <button
            onClick={() => entStore.set(s => ({ ...s, onboardingComplete: true }))}
            className="px-4 py-2 rounded-md bg-accent text-accent-foreground text-[12px] uppercase tracking-wider"
          >{done ? "Re-confirm" : "Mark complete"}</button>
          <Link to="/" className="text-[12px] text-muted-foreground hover:text-foreground uppercase tracking-wider">Open console →</Link>
        </div>
      </Section>
    </Shell>
  );
}
