import { createFileRoute } from "@tanstack/react-router";
import { Shell, PageHeader, Section } from "@/components/apa/Shell";

export const Route = createFileRoute("/app-knowledge")({
  head: () => ({ meta: [{ title: "App Knowledge — APA-OS" }] }),
  component: AppKnowledgePage,
});

const APPS = [
  { name: "Instagram", screens: 24, paths: 9,  fluency: 92 },
  { name: "WhatsApp",  screens: 18, paths: 12, fluency: 96 },
  { name: "Chrome",    screens: 11, paths: 6,  fluency: 88 },
  { name: "YouTube",   screens: 14, paths: 7,  fluency: 84 },
  { name: "Settings",  screens: 32, paths: 18, fluency: 79 },
  { name: "Telegram",  screens: 16, paths: 8,  fluency: 71 },
  { name: "Discord",   screens: 13, paths: 5,  fluency: 64 },
];

function AppKnowledgePage() {
  return (
    <Shell>
      <PageHeader
        eyebrow="Phase 02 · Apps"
        title="App Knowledge."
        lede="What APA understands about each app — its screens, its paths, its quirks. The vocabulary it uses to act."
      />

      <Section title={`Known apps · ${APPS.length}`}>
        <ul className="grid sm:grid-cols-2 lg:grid-cols-3 gap-3">
          {APPS.map(a => (
            <li key={a.name} className="border hairline rounded-md p-4">
              <div className="flex items-baseline justify-between">
                <p className="font-display text-[16px]">{a.name}</p>
                <span className="font-mono text-[11px] text-accent">{a.fluency}%</span>
              </div>
              <p className="mt-1 text-[10px] uppercase tracking-wider text-muted-foreground">
                {a.screens} screens · {a.paths} known paths
              </p>
              <div className="mt-3 h-[2px] bg-[var(--color-border)] rounded">
                <div className="h-full bg-accent" style={{ width: `${a.fluency}%` }} />
              </div>
            </li>
          ))}
        </ul>
      </Section>
    </Shell>
  );
}
