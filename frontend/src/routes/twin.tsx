import { createFileRoute } from "@tanstack/react-router";
import { Shell, PageHeader, Section } from "@/components/apa/Shell";
import { useApa } from "@/lib/apa/store";

export const Route = createFileRoute("/twin")({
  head: () => ({ meta: [{ title: "Digital Twin — APA-OS V2" }] }),
  component: TwinPage,
});

function TwinPage() {
  const twin = useApa(s => s.twin);
  const rows: [string, string][] = [
    ["Sleep cycle", twin.sleep],
    ["Focus window", twin.focusWindow],
    ["Peak study time", twin.studyPeak],
    ["Communication style", twin.style],
    ["Learning speed", twin.learningSpeed],
    ["Preferred surfaces", twin.preferredApps.join(" · ")],
  ];

  return (
    <Shell>
      <PageHeader
        eyebrow="Hidden Layer 03"
        title="Digital Twin."
        lede="A quiet simulation of how you work, rest, decide, and learn. Every plan the system makes is bent toward how you actually live."
      />
      <Section>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-px bg-[var(--color-border)] border hairline">
          {rows.map(([k, v]) => (
            <div key={k} className="bg-background p-7">
              <p className="font-mono text-[10px] uppercase tracking-[0.18em] text-muted-foreground">{k}</p>
              <p className="mt-3 font-display text-xl leading-snug">{v}</p>
            </div>
          ))}
        </div>

        <p className="mt-10 max-w-2xl text-[14px] text-muted-foreground leading-relaxed">
          The twin is never asked to introduce itself. It just bends defaults — a calendar block lands at 8 PM instead of 4 PM; a message reads in your voice instead of a generic one; a revision plan slows down on derivations and speeds up on theory.
        </p>
      </Section>
    </Shell>
  );
}
