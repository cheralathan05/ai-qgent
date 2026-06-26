import { createFileRoute } from "@tanstack/react-router";
import { Shell, PageHeader, Section } from "@/components/apa/Shell";
import { useApa } from "@/lib/apa/store";

export const Route = createFileRoute("/trust")({
  head: () => ({ meta: [{ title: "Trust Center — APA-OS V2" }] }),
  component: TrustPage,
});

function TrustPage() {
  const last = useApa(s => s.outcomes[0]);
  return (
    <Shell>
      <PageHeader
        eyebrow="Hidden Layer 11"
        title="Trust Center."
        lede="Why did it act? What memory did it pull? What permission did it touch? Every answer is here, every time."
      />

      <Section title="Last decision · transparency report">
        {!last ? (
          <p className="text-sm text-muted-foreground italic">No decisions yet. Run an outcome to inspect its rationale.</p>
        ) : (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-px bg-[var(--color-border)] border hairline">
            <div className="bg-background p-7">
              <p className="font-mono text-[10px] uppercase tracking-[0.18em] text-accent">Reasoning</p>
              <p className="mt-3 text-[14px] leading-relaxed">{last.rationale}</p>
              <p className="mt-4 text-[11px] text-muted-foreground">Confidence · {last.confidence}%</p>
            </div>
            <div className="bg-background p-7">
              <p className="font-mono text-[10px] uppercase tracking-[0.18em] text-accent">Memories used</p>
              <ul className="mt-3 space-y-2 text-[13px]">
                <li>· Your 8–10 PM focus window</li>
                <li>· "Deepak" → ATM Protocol partner (corrected once)</li>
                <li>· Compilers exam in 8 days</li>
                <li>· Concise communication style</li>
              </ul>
            </div>
            <div className="bg-background p-7">
              <p className="font-mono text-[10px] uppercase tracking-[0.18em] text-accent">Permissions touched</p>
              <ul className="mt-3 space-y-2 text-[13px]">
                <li>· Calendar — read & write</li>
                <li>· Drive — read</li>
                <li>· WhatsApp — draft only (awaits confirm)</li>
                <li>· No new permissions requested</li>
              </ul>
            </div>
          </div>
        )}
      </Section>

      <Section title="Principles">
        <ul className="space-y-4 max-w-2xl text-[14px] text-muted-foreground leading-relaxed">
          <li>· Nothing is sent without your one-tap confirm, unless you said otherwise.</li>
          <li>· Memories can be inspected, edited, or forgotten at any time.</li>
          <li>· Every autonomous task is logged in Execution Replay.</li>
          <li>· The system never escalates a permission without telling you why.</li>
        </ul>
      </Section>
    </Shell>
  );
}
