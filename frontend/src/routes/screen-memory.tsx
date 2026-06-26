import { createFileRoute } from "@tanstack/react-router";
import { Shell, PageHeader, Section } from "@/components/apa/Shell";

export const Route = createFileRoute("/screen-memory")({
  head: () => ({ meta: [{ title: "Screen Memory — APA-OS" }] }),
  component: ScreenMemoryPage,
});

const HIST = [
  { app: "Instagram", screen: "DM · Deepak", at: 1 },
  { app: "WhatsApp",  screen: "Guru thread", at: 9 },
  { app: "Chrome",    screen: "ATM protocol search", at: 24 },
  { app: "Notion",    screen: "Compilers Unit 4", at: 54 },
  { app: "Drive",     screen: "College › Sem 5", at: 72 },
  { app: "Camera",    screen: "Capture", at: 118 },
];

function ScreenMemoryPage() {
  return (
    <Shell>
      <PageHeader
        eyebrow="Phase 02 · Memory"
        title="Screen Memory."
        lede="Every screen the phone has seen — indexed, searchable, recallable. Visual events you'd otherwise forget."
      />

      <Section title={`Recent · ${HIST.length}`}>
        <div className="grid sm:grid-cols-3 gap-4">
          {HIST.map((h, i) => (
            <article key={i} className="border hairline rounded-md p-4">
              <p className="text-[9px] uppercase tracking-[0.22em] text-accent">{h.app}</p>
              <p className="mt-1 font-display text-[15px] leading-snug">{h.screen}</p>
              <div className="mt-3 h-24 rounded bg-surface flex items-center justify-center text-[10px] text-muted-foreground">
                snapshot · indexed
              </div>
              <p className="mt-2 text-[10px] text-muted-foreground">{h.at}m ago</p>
            </article>
          ))}
        </div>
      </Section>
    </Shell>
  );
}
