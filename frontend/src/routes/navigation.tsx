import { createFileRoute } from "@tanstack/react-router";
import { useState } from "react";
import { Shell, PageHeader, Section } from "@/components/apa/Shell";
import { runOutcome } from "@/lib/apa/orchestrator";

export const Route = createFileRoute("/navigation")({
  head: () => ({ meta: [{ title: "Navigation Assistant — APA-OS" }] }),
  component: NavPage,
});

const KNOWN_PATHS = [
  { goal: "Open Guru Chat",            steps: ["Open WhatsApp", "Tap Chats tab", "Tap Guru"] },
  { goal: "Open Instagram Messages",   steps: ["Open Instagram", "Tap DM icon (top-right)", "Select thread"] },
  { goal: "Navigate to Wi-Fi Settings",steps: ["Open Settings", "Tap Wi-Fi"] },
  { goal: "Open Camera in Selfie mode",steps: ["Open Camera", "Tap flip icon"] },
  { goal: "Send screenshot to Deepak", steps: ["Take Screenshot", "Open WhatsApp · Deepak", "Attach → Gallery → Latest", "Send"] },
];

const SUGGESTIONS = [
  "Open Guru Chat",
  "Navigate To Settings",
  "Open Instagram Messages",
  "Find Compiler PDF in Drive",
];

function NavPage() {
  const [selected, setSelected] = useState(KNOWN_PATHS[0].goal);
  const path = KNOWN_PATHS.find(p => p.goal === selected) ?? KNOWN_PATHS[0];

  return (
    <Shell>
      <PageHeader
        eyebrow="Phase 02 · Navigation"
        title="Navigation Assistant."
        lede="Known paths through every app. Current position, target position, and the cleanest route between them."
      />

      <Section title="Detected screens">
        <div className="flex flex-wrap gap-2">
          {["Instagram · Feed", "WhatsApp · Chats", "Chrome · Search", "Settings · Root", "Notion · Compilers"].map(s => (
            <span key={s} className="text-[11px] px-3 py-1.5 rounded-full border hairline text-foreground">{s}</span>
          ))}
        </div>
      </Section>

      <Section title="Known navigation paths">
        <div className="grid lg:grid-cols-[260px_1fr] gap-6">
          <ul className="space-y-1.5">
            {KNOWN_PATHS.map(p => (
              <li key={p.goal}>
                <button onClick={() => setSelected(p.goal)}
                  className={`w-full text-left px-3 py-2 rounded-md border hairline text-[12.5px] transition
                    ${selected === p.goal ? "bg-surface border-[color:var(--color-border-strong)]" : "hover:bg-surface/60 text-muted-foreground hover:text-foreground"}`}>
                  {p.goal}
                </button>
              </li>
            ))}
          </ul>

          <div>
            <p className="text-[9px] uppercase tracking-[0.22em] text-accent mb-3">Route · {path.goal}</p>
            <ol className="space-y-3">
              {path.steps.map((s, i) => (
                <li key={i} className="flex items-baseline gap-3 text-[13px]">
                  <span className="font-mono text-[10px] text-muted-foreground w-5">{String(i + 1).padStart(2, "0")}</span>
                  <span className="flex-1">{s}</span>
                  <span className="text-[9px] uppercase tracking-wider text-muted-foreground">{i === 0 ? "current" : i === path.steps.length - 1 ? "target" : "transit"}</span>
                </li>
              ))}
            </ol>
            <button onClick={() => runOutcome(path.goal)}
              className="mt-5 px-4 py-2 text-[10px] uppercase tracking-[0.22em] border hairline rounded text-accent hover:bg-accent hover:text-accent-foreground transition">
              Execute path
            </button>
          </div>
        </div>
      </Section>

      <Section title="Suggested actions">
        <div className="flex flex-wrap gap-2">
          {SUGGESTIONS.map(s => (
            <button key={s} onClick={() => runOutcome(s)}
              className="text-[11px] px-3 py-1.5 rounded-full border hairline text-muted-foreground hover:text-accent hover:border-accent transition">
              {s}
            </button>
          ))}
        </div>
      </Section>

      <Section title="Position">
        <div className="grid sm:grid-cols-3 gap-5">
          <Stat label="Current" value="Instagram · Feed" />
          <Stat label="Target" value={path.steps[path.steps.length - 1]} accent />
          <Stat label="Hops" value={`${path.steps.length}`} />
        </div>
      </Section>
    </Shell>
  );
}

function Stat({ label, value, accent }: { label: string; value: string; accent?: boolean }) {
  return (
    <div>
      <p className="text-[9px] uppercase tracking-[0.22em] text-muted-foreground">{label}</p>
      <p className={`mt-2 font-display text-[18px] leading-tight ${accent ? "text-accent" : ""}`}>{value}</p>
    </div>
  );
}
