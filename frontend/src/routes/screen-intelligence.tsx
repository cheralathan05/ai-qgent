import { createFileRoute } from "@tanstack/react-router";
import { Shell, PageHeader, Section } from "@/components/apa/Shell";

export const Route = createFileRoute("/screen-intelligence")({
  head: () => ({ meta: [{ title: "Screen Intelligence — APA-OS" }] }),
  component: ScreenIntelPage,
});

const DETECTED = {
  app: "Instagram",
  screen: "Direct Messages · Deepak",
  text: ["Deepak", "Sent 12:04 AM", "ATM protocol diagram looks tight 🔥", "Type a message…"],
  buttons: ["Back", "Voice", "Video", "Camera", "Gallery", "Send"],
  inputs: ["Message input"],
  icons: ["heart", "comment", "share", "bookmark"],
  navState: "Stack depth 3 · DM thread",
};

function ScreenIntelPage() {
  return (
    <Shell>
      <PageHeader
        eyebrow="Phase 02 · Vision"
        title="Screen Intelligence."
        lede="The phone, read in plain language. What's on screen, what can be touched, what state we're in."
      />

      <Section title="Now showing">
        <div className="grid sm:grid-cols-3 gap-5">
          <Card label="App" value={DETECTED.app} accent />
          <Card label="Screen" value={DETECTED.screen} />
          <Card label="Nav state" value={DETECTED.navState} />
        </div>
      </Section>

      <div className="grid lg:grid-cols-2 gap-7 border-t hairline px-7 py-7">
        <Block title="Detected text">
          <ul className="space-y-1.5">
            {DETECTED.text.map((t, i) => (
              <li key={i} className="text-[12.5px] text-foreground/90">"{t}"</li>
            ))}
          </ul>
        </Block>
        <Block title="Detected buttons">
          <div className="flex flex-wrap gap-2">
            {DETECTED.buttons.map(b => (
              <span key={b} className="px-2.5 py-1 border hairline rounded text-[11px] text-accent">{b}</span>
            ))}
          </div>
        </Block>
        <Block title="Detected inputs">
          <ul className="space-y-1.5">
            {DETECTED.inputs.map(i => <li key={i} className="text-[12.5px]">{i}</li>)}
          </ul>
        </Block>
        <Block title="Detected icons">
          <div className="flex flex-wrap gap-2">
            {DETECTED.icons.map(i => (
              <span key={i} className="px-2.5 py-1 border hairline rounded text-[11px] text-muted-foreground">{i}</span>
            ))}
          </div>
        </Block>
      </div>
    </Shell>
  );
}

function Card({ label, value, accent }: { label: string; value: string; accent?: boolean }) {
  return (
    <div>
      <p className="text-[9px] uppercase tracking-[0.22em] text-muted-foreground">{label}</p>
      <p className={`mt-2 font-display text-[20px] ${accent ? "text-accent" : ""}`}>{value}</p>
    </div>
  );
}

function Block({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div>
      <p className="text-[9px] uppercase tracking-[0.22em] text-muted-foreground mb-3">{title}</p>
      {children}
    </div>
  );
}
