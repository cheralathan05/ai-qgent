import { createFileRoute } from "@tanstack/react-router";
import { Shell, PageHeader, Section } from "@/components/apa/Shell";
import { useApa } from "@/lib/apa/store";

export const Route = createFileRoute("/phone-intelligence")({
  head: () => ({ meta: [{ title: "Phone Intelligence — APA-OS" }] }),
  component: PhoneIntelPage,
});

const HISTORY = [
  { app: "Instagram", at: Date.now() - 1000 * 60 * 1,   screen: "Feed" },
  { app: "Instagram", at: Date.now() - 1000 * 60 * 6,   screen: "DM · Deepak" },
  { app: "WhatsApp",  at: Date.now() - 1000 * 60 * 14,  screen: "Chat · Guru" },
  { app: "Chrome",    at: Date.now() - 1000 * 60 * 27,  screen: "Search · ATM protocol" },
  { app: "Notion",    at: Date.now() - 1000 * 60 * 52,  screen: "Compilers Unit 4" },
  { app: "Spotify",   at: Date.now() - 1000 * 60 * 88,  screen: "Focus playlist" },
  { app: "Camera",    at: Date.now() - 1000 * 60 * 124, screen: "Capture" },
];

const BATTERY_TREND = [88, 86, 84, 81, 78, 76, 74, 72, 72, 72];

function PhoneIntelPage() {
  const devices = useApa(s => s.devices);
  const phone = devices.find(d => d.kind === "phone");
  const current = HISTORY[0];
  const previous = HISTORY[1];

  return (
    <Shell>
      <PageHeader
        eyebrow="Phase 02 · Intelligence"
        title="Phone Intelligence."
        lede="What's open, what was open, how the battery's trending, what app holds focus right now. The phone, finally legible."
      />

      <Section title="State">
        <div className="grid sm:grid-cols-4 gap-5">
          <Stat label="Current app" value={current.app} accent />
          <Stat label="Previous app" value={previous.app} />
          <Stat label="Foreground" value={current.screen} />
          <Stat label="Network" value="Wi-Fi · home" />
        </div>
      </Section>

      <Section title="Battery trend (last 60m)">
        <BatterySpark data={BATTERY_TREND} />
        <p className="mt-3 text-[11px] text-muted-foreground">
          {phone?.battery ?? 72}% · steady drain · projected 4h 12m at this rate.
        </p>
      </Section>

      <Section title="Navigation history">
        <ul className="divide-y hairline">
          {HISTORY.map((h, i) => (
            <li key={i} className="py-3 grid grid-cols-[110px_140px_1fr] gap-5 items-baseline text-[12.5px]">
              <span className="font-mono text-[10px] uppercase tracking-wider text-muted-foreground">
                {rel(h.at)}
              </span>
              <span className="text-foreground">{h.app}</span>
              <span className="text-muted-foreground">{h.screen}</span>
            </li>
          ))}
        </ul>
      </Section>

      <Section title="Screen memory">
        <div className="grid sm:grid-cols-3 gap-4">
          {HISTORY.slice(0, 6).map((h, i) => (
            <div key={i} className="border hairline rounded-md p-4">
              <p className="text-[9px] uppercase tracking-[0.22em] text-accent">{h.app}</p>
              <p className="mt-1 font-display text-[14px]">{h.screen}</p>
              <p className="mt-2 text-[10px] text-muted-foreground">{rel(h.at)} · indexed</p>
            </div>
          ))}
        </div>
      </Section>
    </Shell>
  );
}

function rel(at: number) {
  const m = Math.round((Date.now() - at) / 60000);
  return m < 1 ? "now" : m < 60 ? `${m}m ago` : `${Math.round(m / 60)}h ago`;
}

function BatterySpark({ data }: { data: number[] }) {
  const w = 600, h = 80;
  const max = 100, min = 0;
  const points = data.map((v, i) => {
    const x = (i / (data.length - 1)) * w;
    const y = h - ((v - min) / (max - min)) * h;
    return `${x.toFixed(1)},${y.toFixed(1)}`;
  }).join(" ");
  return (
    <svg viewBox={`0 0 ${w} ${h}`} className="w-full h-20">
      <polyline fill="none" stroke="var(--color-accent)" strokeWidth="1.5" points={points} />
      {data.map((v, i) => {
        const x = (i / (data.length - 1)) * w;
        const y = h - ((v - min) / (max - min)) * h;
        return <circle key={i} cx={x} cy={y} r="2" fill="var(--color-accent)" />;
      })}
    </svg>
  );
}

function Stat({ label, value, accent }: { label: string; value: string; accent?: boolean }) {
  return (
    <div>
      <p className="text-[9px] uppercase tracking-[0.22em] text-muted-foreground">{label}</p>
      <p className={`mt-2 font-display text-[20px] leading-tight ${accent ? "text-accent" : ""}`}>{value}</p>
    </div>
  );
}
