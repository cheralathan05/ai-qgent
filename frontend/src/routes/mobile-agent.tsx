import { createFileRoute } from "@tanstack/react-router";
import { Shell, PageHeader, Section } from "@/components/apa/Shell";
import { useApa } from "@/lib/apa/store";

export const Route = createFileRoute("/mobile-agent")({
  head: () => ({ meta: [{ title: "Mobile Agent — APA-OS" }] }),
  component: MobileAgentPage,
});

function MobileAgentPage() {
  const phone = useApa(s => s.devices.find(d => d.kind === "phone"));

  return (
    <Shell>
      <PageHeader
        eyebrow="Onboarding · 6"
        title="Mobile Agent."
        lede="The APK on your phone — version, heartbeat, capabilities. The bridge between you and APA-OS."
      />

      <Section title="Status">
        <div className="grid sm:grid-cols-4 gap-5">
          <Stat label="Agent version" value="v0.9.4" accent />
          <Stat label="Last heartbeat" value="just now" />
          <Stat label="Connection" value={phone ? "secure" : "offline"} />
          <Stat label="Sync health" value="98%" />
        </div>
      </Section>

      <Section title="Capabilities">
        <ul className="grid sm:grid-cols-2 gap-2">
          {(phone?.capabilities ?? []).map(c => (
            <li key={c} className="border hairline rounded px-3 py-2 text-[12px]">{c}</li>
          ))}
        </ul>
      </Section>

      <Section title="Permissions">
        <ul className="divide-y hairline">
          {[
            ["Notifications", "granted"], ["Accessibility", "granted"], ["Storage", "granted"],
            ["Microphone", "granted"], ["Camera", "ask"], ["Location", "denied"],
          ].map(([k, v]) => (
            <li key={k} className="py-2.5 grid grid-cols-[1fr_120px] text-[12.5px]">
              <span>{k}</span>
              <span className={`text-right text-[10px] uppercase tracking-[0.22em] ${v === "granted" ? "text-[color:var(--color-success)]" : v === "denied" ? "text-destructive" : "text-warn"}`}>{v}</span>
            </li>
          ))}
        </ul>
      </Section>
    </Shell>
  );
}

function Stat({ label, value, accent }: { label: string; value: string; accent?: boolean }) {
  return (
    <div>
      <p className="text-[9px] uppercase tracking-[0.22em] text-muted-foreground">{label}</p>
      <p className={`mt-2 font-display text-[20px] ${accent ? "text-accent" : ""}`}>{value}</p>
    </div>
  );
}
