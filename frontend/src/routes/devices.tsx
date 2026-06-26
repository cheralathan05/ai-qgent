import { createFileRoute } from "@tanstack/react-router";
import { useState } from "react";
import { Shell, PageHeader, Section } from "@/components/apa/Shell";
import { useApa } from "@/lib/apa/store";

export const Route = createFileRoute("/devices")({
  head: () => ({ meta: [{ title: "Live Device Center — APA-OS V3" }] }),
  component: DevicesPage,
});

function rel(ts: number) {
  const s = Math.round((Date.now() - ts) / 1000);
  if (s < 60) return `${s}s ago`;
  if (s < 3600) return `${Math.round(s / 60)}m ago`;
  return `${Math.round(s / 3600)}h ago`;
}

const PHONE_APPS = [
  "Instagram","WhatsApp","Chrome","Gallery","Notion","Spotify","YouTube","Drive","Mail","Calendar","Maps","Camera",
];

function DevicesPage() {
  const devices = useApa(s => s.devices);
  const outcomes = useApa(s => s.outcomes);
  const focused = outcomes[0];
  const [activeId, setActiveId] = useState(devices.find(d => d.kind === "phone")?.id ?? devices[0]?.id);
  const active = devices.find(d => d.id === activeId);
  const phoneControlling = focused?.category === "Device control";

  return (
    <Shell>
      <PageHeader
        eyebrow="Hidden Layer 09"
        title="Live Device Center."
        lede="Not an inventory. The action layer. Every surface APA-OS can see, talk to, or quietly watch — with live vision overlays and execution verification."
      />

      <Section title="Command center" aside={
        <p className="font-mono text-[10px] uppercase tracking-wider text-muted-foreground">
          {devices.filter(d => d.status !== "offline").length} online · {devices.filter(d => d.status === "connected").length} controllable
        </p>
      }>
        <ul className="grid grid-cols-2 md:grid-cols-3 gap-px bg-[var(--color-border)] border hairline">
          {devices.map(d => (
            <li key={d.id}>
              <button
                onClick={() => setActiveId(d.id)}
                className={[
                  "w-full text-left p-5 transition",
                  d.id === activeId ? "bg-surface" : "bg-background hover:bg-surface/60",
                ].join(" ")}
              >
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <p className="font-mono text-[10px] uppercase tracking-[0.18em] text-muted-foreground">{d.kind}</p>
                    <p className="mt-1.5 font-display text-xl tracking-tight">{d.name}</p>
                    <p className="mt-1 text-[11px] text-muted-foreground">Last sync · {rel(d.lastSync)}</p>
                  </div>
                  <span
                    className="rounded-full px-2 py-0.5 text-[10px] border hairline shrink-0"
                    style={{
                      color: d.status === "connected" || d.status === "controlling" ? "var(--color-success)"
                           : d.status === "observed"  ? "var(--color-accent)"
                           : "var(--color-muted-foreground)",
                    }}
                  >{d.status}</span>
                </div>
                {d.capabilities && (
                  <p className="mt-3 text-[10.5px] text-muted-foreground line-clamp-1">
                    {d.capabilities.join(" · ")}
                  </p>
                )}
              </button>
            </li>
          ))}
        </ul>
      </Section>

      {active && (
        <Section title={`${active.name} — live`}>
          <div className="grid grid-cols-1 lg:grid-cols-[280px_1fr_280px] gap-px bg-[var(--color-border)] border hairline">
            {/* Phone frame */}
            <div className="bg-background p-6 flex items-center justify-center">
              {active.kind === "phone" ? (
                <PhoneFrame controlling={phoneControlling} />
              ) : (
                <div className="text-center text-muted-foreground">
                  <p className="font-mono text-[10px] uppercase tracking-wider">{active.kind}</p>
                  <p className="mt-2 text-[13px]">No live mirror</p>
                  <p className="mt-1 text-[11px]">Use vision agent to observe</p>
                </div>
              )}
            </div>

            {/* Live screen + execution */}
            <div className="bg-background p-6">
              <p className="font-mono text-[10px] uppercase tracking-wider text-accent">Live screen</p>
              <div className="mt-3 aspect-video rounded-lg border hairline bg-[var(--color-surface)] relative overflow-hidden">
                <div className="absolute inset-0 grid grid-cols-4 gap-2 p-4">
                  {PHONE_APPS.slice(0, 8).map(app => (
                    <div key={app} className="rounded-md border hairline bg-background flex flex-col items-center justify-center text-[10px]">
                      <span className="h-6 w-6 rounded-md bg-accent/30 mb-1" />
                      {app}
                    </div>
                  ))}
                </div>
                {phoneControlling && (
                  <div className="absolute inset-0 pointer-events-none">
                    <div className="absolute top-4 left-4 px-2 py-1 rounded border border-accent text-[10px] text-accent bg-background/60">
                      Instagram · 0.97
                    </div>
                    <div className="absolute top-3 left-3 right-[68%] bottom-[68%] border-2 border-accent rounded-md apa-pulse" />
                  </div>
                )}
                <div className="absolute bottom-2 left-3 font-mono text-[9px] uppercase tracking-wider text-muted-foreground">
                  {phoneControlling ? "vision overlay · live" : "observing"}
                </div>
              </div>

              <p className="mt-5 font-mono text-[10px] uppercase tracking-wider text-accent">Execution stream</p>
              <ul className="mt-2 font-mono text-[11.5px] space-y-1">
                {(focused?.executionLog ?? []).slice(-6).map((l, i) => (
                  <li key={i} className="flex gap-3 apa-fade-up">
                    <span className="text-success">✓</span>
                    <span className="text-muted-foreground">{new Date(l.at).toLocaleTimeString([], { hour:"2-digit",minute:"2-digit",second:"2-digit" })}</span>
                    <span>{l.label}</span>
                  </li>
                ))}
                {(!focused || focused.executionLog.length === 0) && (
                  <li className="text-muted-foreground italic">No device actions yet.</li>
                )}
              </ul>
            </div>

            {/* Capabilities + AI sees */}
            <div className="bg-background p-6">
              <p className="font-mono text-[10px] uppercase tracking-wider text-accent">Capabilities</p>
              <ul className="mt-2 space-y-1 text-[12.5px]">
                {(active.capabilities ?? []).map(c => (
                  <li key={c} className="flex items-center gap-2">
                    <span className="text-success">✓</span>{c}
                  </li>
                ))}
              </ul>

              <p className="mt-6 font-mono text-[10px] uppercase tracking-wider text-accent">AI sees</p>
              <ul className="mt-2 flex flex-wrap gap-1.5">
                {PHONE_APPS.slice(0, 8).map(a => (
                  <li key={a} className="rounded-md border hairline px-2 py-0.5 text-[10.5px] text-muted-foreground">{a}</li>
                ))}
              </ul>

              <p className="mt-6 font-mono text-[10px] uppercase tracking-wider text-accent">Health</p>
              <ul className="mt-2 space-y-1 text-[11.5px]">
                {active.battery && <Row k="Battery" v={`${active.battery}%`} />}
                <Row k="Latency" v="220ms" />
                <Row k="Screen" v="Available" />
                <Row k="Permission" v="Read · Tap · Type" />
              </ul>
            </div>
          </div>
        </Section>
      )}
    </Shell>
  );
}

function Row({ k, v }: { k: string; v: string }) {
  return (
    <li className="flex items-baseline justify-between">
      <span className="font-mono text-[9.5px] uppercase tracking-wider text-muted-foreground">{k}</span>
      <span>{v}</span>
    </li>
  );
}

function PhoneFrame({ controlling }: { controlling: boolean }) {
  return (
    <div className="relative w-[200px] h-[400px] rounded-[36px] border-2 hairline-strong bg-background p-2 shadow-2xl">
      <div className="absolute top-2 left-1/2 -translate-x-1/2 h-4 w-20 rounded-b-xl bg-background z-10" />
      <div className="h-full w-full rounded-[28px] bg-[var(--color-surface)] overflow-hidden relative">
        <div className="absolute inset-0 grid grid-cols-3 gap-2 p-3 pt-8">
          {PHONE_APPS.slice(0, 9).map(app => (
            <div key={app} className="flex flex-col items-center text-[8px]">
              <span className="h-7 w-7 rounded-md bg-accent/30 mb-0.5" />
              <span className="text-foreground/80 truncate w-full text-center">{app}</span>
            </div>
          ))}
        </div>
        {controlling && (
          <div className="absolute top-7 left-2 right-[58%] h-12 border-2 border-accent rounded-md apa-pulse" />
        )}
      </div>
      <div className={`absolute -bottom-6 left-1/2 -translate-x-1/2 font-mono text-[9px] uppercase tracking-wider ${
        controlling ? "text-accent" : "text-success"
      }`}>
        {controlling ? "controlling" : "connected"}
      </div>
    </div>
  );
}
