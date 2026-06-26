import { createFileRoute } from "@tanstack/react-router";
import { Shell, PageHeader, Section } from "@/components/apa/Shell";
import { entStore, useEnt } from "@/lib/apa/enterprise";

export const Route = createFileRoute("/settings")({
  head: () => ({ meta: [{ title: "Settings — APA-OS" }] }),
  component: SettingsPage,
});

function SettingsPage() {
  const flags = useEnt(s => s.flags);
  const prefs = useEnt(s => s.prefs);

  function toggleFlag(k: keyof typeof flags) {
    entStore.set(s => ({ ...s, flags: { ...s.flags, [k]: !s.flags[k] } }));
  }
  function togglePref(k: keyof typeof prefs) {
    entStore.set(s => ({ ...s, prefs: { ...s.prefs, [k]: !s.prefs[k] } }));
  }

  return (
    <Shell>
      <PageHeader eyebrow="Personalize" title="Settings."
        lede="Feature flags, accessibility, personalization. Everything is reversible." />
      <Section title="Feature flags">
        <ul className="border hairline rounded-md divide-y divide-[var(--color-border)]">
          {(Object.keys(flags) as (keyof typeof flags)[]).map(k => (
            <Toggle key={k} label={labelize(k)} on={flags[k]} onClick={() => toggleFlag(k)} />
          ))}
        </ul>
      </Section>
      <Section title="Accessibility & motion">
        <ul className="border hairline rounded-md divide-y divide-[var(--color-border)]">
          <Toggle label="High contrast mode" on={prefs.highContrast} onClick={() => togglePref("highContrast")} />
          <Toggle label="Reduced motion"     on={prefs.reducedMotion} onClick={() => togglePref("reducedMotion")} />
        </ul>
      </Section>
      <Section title="Security">
        <ul className="text-[12.5px] space-y-2">
          <li className="flex justify-between border hairline rounded-md px-4 py-2.5"><span>Active sessions</span><span className="font-mono text-[10.5px] text-muted-foreground">2 · MacBook, iPhone</span></li>
          <li className="flex justify-between border hairline rounded-md px-4 py-2.5"><span>Trusted devices</span><span className="font-mono text-[10.5px] text-muted-foreground">5 / 6</span></li>
          <li className="flex justify-between border hairline rounded-md px-4 py-2.5"><span>Session timeout</span><span className="font-mono text-[10.5px] text-muted-foreground">30 min</span></li>
          <li className="flex justify-between border hairline rounded-md px-4 py-2.5"><span>Last login</span><span className="font-mono text-[10.5px] text-muted-foreground">Today · 09:14</span></li>
        </ul>
      </Section>
      <Section title="Keyboard">
        <ul className="grid grid-cols-2 md:grid-cols-4 gap-3 text-[11.5px]">
          {[
            ["⌘K", "Command center"],
            ["⌘/", "Toggle Copilot"],
            ["⌘⇧P", "Quick palette"],
            ["Alt 1..9", "Jump to layer"],
            ["Esc", "Close any overlay"],
            ["Double-space", "Voice"],
          ].map(([k, v]) => (
            <li key={k as string} className="border hairline rounded-md px-3 py-2 flex justify-between">
              <span>{v}</span><kbd className="font-mono text-[10px] text-accent">{k}</kbd>
            </li>
          ))}
        </ul>
      </Section>
    </Shell>
  );
}

function labelize(s: string) { return s.replace(/([A-Z])/g, " $1").replace(/^./, c => c.toUpperCase()); }

function Toggle({ label, on, onClick }: { label: string; on: boolean; onClick: () => void }) {
  return (
    <li className="flex items-center justify-between px-4 py-3">
      <span className="text-[13px]">{label}</span>
      <button
        onClick={onClick}
        aria-pressed={on}
        className={["relative h-5 w-9 rounded-full transition", on ? "bg-accent" : "bg-[var(--color-border-strong)]"].join(" ")}
      >
        <span className={["absolute top-0.5 h-4 w-4 rounded-full bg-background transition", on ? "left-[18px]" : "left-0.5"].join(" ")} />
      </button>
    </li>
  );
}
