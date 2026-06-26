import { createFileRoute } from "@tanstack/react-router";
import { Shell, PageHeader, Section } from "@/components/apa/Shell";

export const Route = createFileRoute("/emergency")({
  head: () => ({ meta: [{ title: "Emergency Copilot — APA-OS V2" }] }),
  component: EmergencyPage,
});

function EmergencyPage() {
  return (
    <Shell>
      <PageHeader
        eyebrow="Hidden Layer 14"
        title="Emergency Copilot."
        lede="When a deadline is hours away, defaults change. Notifications quiet. The plan gets shorter. Distractions are removed without asking."
      />

      <Section>
        <div className="rounded-xl border hairline-strong bg-surface/40 p-8 glow-ochre">
          <div className="flex items-center gap-3">
            <span className="h-2 w-2 rounded-full bg-warn apa-pulse" />
            <p className="font-mono text-[10px] uppercase tracking-[0.22em] text-warn">Mode armed</p>
          </div>
          <p className="mt-4 font-display text-3xl tracking-tight">Compilers exam in 14h 22m.</p>
          <p className="mt-2 text-muted-foreground text-[14px]">
            Switching to emergency defaults. The system will rebuild your evening around revision and silence non-essential channels.
          </p>

          <div className="mt-8 grid grid-cols-1 md:grid-cols-2 gap-px bg-[var(--color-border)] border hairline">
            <Block title="Revision sprint built" detail="3 sessions of 45 minutes, weighted by predicted weak topics: Unit 4 > Unit 5 > Unit 3." />
            <Block title="Focus mode armed"      detail="Phone DND from 7:50 PM. Laptop opens revision workspace at 7:55 PM." />
            <Block title="Distractions paused"   detail="WhatsApp group muted. Email digest deferred until tomorrow morning." />
            <Block title="Safety net"            detail="Wake alarm 7:15 AM. Quick-review deck prepared for the bus ride." />
          </div>
        </div>
      </Section>

      <Section title="When the system enters this mode automatically">
        <ul className="space-y-3 max-w-2xl text-[14px] text-muted-foreground leading-relaxed">
          <li>· A deadline crosses the 24-hour threshold and readiness is below 75%.</li>
          <li>· An unexpected announcement compresses your timeline (rescheduled exam, surprise quiz).</li>
          <li>· Two consecutive nights of sleep loss + an important morning event.</li>
        </ul>
      </Section>
    </Shell>
  );
}

function Block({ title, detail }: { title: string; detail: string }) {
  return (
    <div className="bg-background p-6">
      <p className="font-display text-lg">{title}</p>
      <p className="mt-2 text-[13px] text-muted-foreground leading-relaxed">{detail}</p>
    </div>
  );
}
