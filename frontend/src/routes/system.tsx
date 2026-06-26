import { createFileRoute } from "@tanstack/react-router";
import { Shell, PageHeader, Section } from "@/components/apa/Shell";
import { useApa } from "@/lib/apa/store";

export const Route = createFileRoute("/system")({
  head: () => ({ meta: [{ title: "System Health — APA-OS" }] }),
  component: SystemPage,
});

const SERVICES = [
  { name: "Backend",   tone: "success", load: "32%",  latency: "41ms" },
  { name: "Database",  tone: "success", load: "18%",  latency: "9ms"  },
  { name: "Redis",     tone: "success", load: "11%",  latency: "2ms"  },
  { name: "Ollama",    tone: "warn",    load: "78%",  latency: "210ms"},
  { name: "WebSocket", tone: "success", load: "23%",  latency: "live" },
  { name: "Queue",     tone: "success", load: "7 jobs", latency: "—"  },
] as const;

function SystemPage() {
  const devices = useApa(s => s.devices);
  return (
    <Shell>
      <PageHeader eyebrow="Operations" title="System Health."
        lede="Every backbone the OS depends on. Live." />
      <Section title="Services">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-px bg-[var(--color-border)] border hairline">
          {SERVICES.map(s => (
            <div key={s.name} className="bg-background p-5">
              <div className="flex items-center justify-between">
                <p className="font-display text-[18px]">{s.name}</p>
                <span className="h-1.5 w-1.5 rounded-full apa-pulse"
                  style={{ background: s.tone === "success" ? "var(--color-success)" : "var(--color-warn)" }} />
              </div>
              <div className="mt-4 grid grid-cols-2 gap-3 text-[11px]">
                <div><p className="text-muted-foreground uppercase tracking-wider text-[9px]">Load</p><p className="font-mono mt-1">{s.load}</p></div>
                <div><p className="text-muted-foreground uppercase tracking-wider text-[9px]">Latency</p><p className="font-mono mt-1">{s.latency}</p></div>
              </div>
            </div>
          ))}
        </div>
      </Section>
      <Section title="Connected devices">
        <ul className="space-y-2">
          {devices.map(d => (
            <li key={d.id} className="flex items-center justify-between border hairline rounded-md px-4 py-2.5">
              <span className="text-[13px]">{d.name}</span>
              <span className="font-mono text-[10px] uppercase tracking-wider"
                style={{ color: d.status === "offline" ? "var(--color-muted-foreground)" : "var(--color-success)" }}>{d.status}</span>
            </li>
          ))}
        </ul>
      </Section>
    </Shell>
  );
}
