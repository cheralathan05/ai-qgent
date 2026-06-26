import { createFileRoute, Link } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { Shell, PageHeader, Section } from "@/components/apa/Shell";

export const Route = createFileRoute("/device-connect")({
  head: () => ({ meta: [{ title: "Connect Device — APA-OS" }] }),
  component: DeviceConnectPage,
});

const STAGES = ["Scanning", "Authenticating", "Registering device", "Secure channel", "Syncing", "Connected"] as const;

function DeviceConnectPage() {
  const [stage, setStage] = useState(0);
  const [pairCode] = useState(() => Math.random().toString(36).slice(2, 8).toUpperCase());

  useEffect(() => {
    if (stage >= STAGES.length - 1) return;
    const t = setTimeout(() => setStage(s => Math.min(s + 1, STAGES.length - 1)), 1400);
    return () => clearTimeout(t);
  }, [stage]);

  return (
    <Shell>
      <PageHeader
        eyebrow="Onboarding · 5"
        title="Connect your phone."
        lede="Install the APA-OS Agent on Android. Scan the code. The phone becomes part of your operating system."
      />

      <div className="grid lg:grid-cols-[1fr_360px] gap-0 border-t hairline">
        <div className="px-7 py-8">
          <div className="aspect-square max-w-[320px] mx-auto border-2 hairline-strong rounded-2xl p-4 flex items-center justify-center bg-surface/40">
            <QrPlaceholder code={pairCode} />
          </div>
          <p className="mt-5 text-center font-mono text-[18px] tracking-[0.4em] text-accent">{pairCode}</p>
          <p className="mt-2 text-center text-[11px] text-muted-foreground">Pair code · expires in 5 min</p>
        </div>

        <aside className="border-l hairline px-6 py-8">
          <p className="text-[9px] uppercase tracking-[0.22em] text-muted-foreground mb-4">Pairing sequence</p>
          <ol className="space-y-3">
            {STAGES.map((s, i) => (
              <li key={s} className="flex items-baseline gap-3">
                <span className={`h-1.5 w-1.5 rounded-full ${i < stage ? "bg-[color:var(--color-success)]" : i === stage ? "bg-accent apa-pulse" : "bg-muted-foreground/30"}`} />
                <span className={`text-[13px] ${i <= stage ? "text-foreground" : "text-muted-foreground"}`}>{s}</span>
              </li>
            ))}
          </ol>

          {stage === STAGES.length - 1 && (
            <Link to="/devices" className="mt-7 block text-center px-4 py-3 border hairline-strong rounded-md text-[11px] uppercase tracking-[0.22em] hover:text-accent hover:border-accent">
              Open device dashboard →
            </Link>
          )}
        </aside>
      </div>

      <Section title="What you'll grant">
        <ul className="grid sm:grid-cols-2 gap-3">
          {[
            ["Files", "Find your screenshots and notes when you need them."],
            ["Notifications", "So APA can dismiss noise and surface signal."],
            ["Calendar", "Block focus time, remember deadlines."],
            ["Microphone", "Voice control — push-to-talk, wake word."],
          ].map(([k, v]) => (
            <li key={k} className="border hairline rounded-md p-4">
              <p className="text-[9px] uppercase tracking-[0.22em] text-accent">{k}</p>
              <p className="mt-1 text-[12px] text-muted-foreground">{v}</p>
            </li>
          ))}
        </ul>
      </Section>
    </Shell>
  );
}

function QrPlaceholder({ code }: { code: string }) {
  const cells = 21;
  const seed = code.split("").reduce((a, c) => a + c.charCodeAt(0), 0);
  return (
    <svg viewBox={`0 0 ${cells} ${cells}`} className="w-full h-full">
      {Array.from({ length: cells * cells }).map((_, i) => {
        const x = i % cells, y = Math.floor(i / cells);
        const corner = (x < 7 && y < 7) || (x >= cells - 7 && y < 7) || (x < 7 && y >= cells - 7);
        const on = corner ? ((x === 0 || x === 6 || y === 0 || y === 6) || (x >= 2 && x <= 4 && y >= 2 && y <= 4)) : ((seed * (x + 1) * (y + 1)) % 3 === 0);
        return on ? <rect key={i} x={x} y={y} width={1} height={1} fill="currentColor" /> : null;
      })}
    </svg>
  );
}
