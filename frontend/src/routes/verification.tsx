import { createFileRoute } from "@tanstack/react-router";
import { Shell, PageHeader, Section } from "@/components/apa/Shell";

export const Route = createFileRoute("/verification")({
  head: () => ({ meta: [{ title: "Visual Verification — APA-OS" }] }),
  component: VerificationPage,
});

const CHECKS = [
  { id: "v1", screen: "WhatsApp · Deepak thread", expected: "Message sent indicator visible", confidence: 0.97, status: "ok" as const },
  { id: "v2", screen: "Instagram · Profile",      expected: "Username matches @deepak.k",     confidence: 0.93, status: "ok" as const },
  { id: "v3", screen: "Chrome · Drive search",    expected: "ATM Protocol.pdf at top",        confidence: 0.71, status: "warn" as const },
  { id: "v4", screen: "Settings · Focus mode",    expected: "Focus mode toggle ON",           confidence: 0.99, status: "ok" as const },
];

function VerificationPage() {
  return (
    <Shell>
      <PageHeader
        eyebrow="Phase 02 · Trust"
        title="Visual Verification."
        lede="After every action, the screen is read back to confirm reality matches intent. No claim without evidence."
      />

      <Section title={`Recent verifications · ${CHECKS.length}`}>
        <ul className="divide-y hairline">
          {CHECKS.map(c => (
            <li key={c.id} className="py-4 grid grid-cols-[1fr_120px_80px] gap-4 items-baseline">
              <div>
                <p className="text-[9px] uppercase tracking-[0.22em] text-accent">{c.screen}</p>
                <p className="mt-1 text-[13px]">{c.expected}</p>
              </div>
              <span className="font-mono text-[11px] text-muted-foreground">{Math.round(c.confidence * 100)}% confidence</span>
              <span className={`text-[10px] uppercase tracking-[0.22em] text-right ${c.status === "ok" ? "text-[color:var(--color-success)]" : "text-warn"}`}>
                {c.status === "ok" ? "verified" : "review"}
              </span>
            </li>
          ))}
        </ul>
      </Section>
    </Shell>
  );
}
