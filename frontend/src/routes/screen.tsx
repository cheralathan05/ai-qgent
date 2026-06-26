import { createFileRoute } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { Shell, PageHeader, Section } from "@/components/apa/Shell";
import { useApa } from "@/lib/apa/store";

export const Route = createFileRoute("/screen")({
  head: () => ({ meta: [{ title: "Screen Viewer — APA-OS" }] }),
  component: ScreenPage,
});

type Detect = { id: string; kind: "button" | "input" | "text" | "icon"; label: string; x: number; y: number; w: number; h: number; conf: number };

const APPS: Record<string, { app: string; screen: string; detects: Detect[] }> = {
  whatsapp: {
    app: "WhatsApp", screen: "Chats list",
    detects: [
      { id: "d1", kind: "icon",  label: "Search",       x: 8,  y: 6,  w: 8,  h: 5,  conf: 98 },
      { id: "d2", kind: "icon",  label: "Camera",       x: 84, y: 6,  w: 8,  h: 5,  conf: 95 },
      { id: "d3", kind: "text",  label: "Deepak",       x: 18, y: 22, w: 40, h: 4,  conf: 99 },
      { id: "d4", kind: "text",  label: "Mom",          x: 18, y: 33, w: 30, h: 4,  conf: 99 },
      { id: "d5", kind: "text",  label: "Guru Chat",    x: 18, y: 44, w: 40, h: 4,  conf: 97 },
      { id: "d6", kind: "button",label: "New chat",     x: 78, y: 88, w: 14, h: 8,  conf: 96 },
    ],
  },
  instagram: {
    app: "Instagram", screen: "Feed",
    detects: [
      { id: "d1", kind: "icon",  label: "Home",         x: 4,  y: 92, w: 8,  h: 6,  conf: 99 },
      { id: "d2", kind: "icon",  label: "Search",       x: 22, y: 92, w: 8,  h: 6,  conf: 99 },
      { id: "d3", kind: "icon",  label: "Reels",        x: 40, y: 92, w: 8,  h: 6,  conf: 99 },
      { id: "d4", kind: "icon",  label: "DM",           x: 88, y: 6,  w: 8,  h: 5,  conf: 97 },
      { id: "d5", kind: "button",label: "Like",         x: 6,  y: 64, w: 8,  h: 5,  conf: 94 },
      { id: "d6", kind: "button",label: "Comment",      x: 16, y: 64, w: 8,  h: 5,  conf: 94 },
    ],
  },
  settings: {
    app: "Settings", screen: "Root",
    detects: [
      { id: "d1", kind: "text",  label: "Wi-Fi",        x: 8,  y: 18, w: 60, h: 5,  conf: 99 },
      { id: "d2", kind: "text",  label: "Bluetooth",    x: 8,  y: 28, w: 60, h: 5,  conf: 99 },
      { id: "d3", kind: "text",  label: "Display",      x: 8,  y: 38, w: 60, h: 5,  conf: 99 },
      { id: "d4", kind: "input", label: "Search",       x: 8,  y: 8,  w: 84, h: 5,  conf: 95 },
    ],
  },
};

function ScreenPage() {
  const devices = useApa(s => s.devices);
  const phone = devices.find(d => d.kind === "phone");
  const [appKey, setAppKey] = useState<keyof typeof APPS>("whatsapp");
  const [showOcr, setShowOcr] = useState(true);
  const [showBoxes, setShowBoxes] = useState(true);
  const [zoom, setZoom] = useState(1);
  const [tick, setTick] = useState(0);
  useEffect(() => {
    const t = setInterval(() => setTick(x => x + 1), 4000);
    return () => clearInterval(t);
  }, []);

  const data = APPS[appKey];

  return (
    <Shell>
      <PageHeader
        eyebrow="Phase 02 · Vision"
        title="Screen Viewer."
        lede="See what the phone sees. Real-time mirror with OCR overlays, detected buttons, icons, and text — refreshed live."
      />

      <div className="grid lg:grid-cols-[1fr_320px] gap-0 border-t hairline">
        <div className="px-7 py-7 flex items-center justify-center bg-[radial-gradient(ellipse_at_center,_var(--color-surface)_0%,_transparent_70%)] min-h-[78vh]">
          <PhoneFrame zoom={zoom}>
            <div className="absolute inset-0 bg-[var(--color-surface)]">
              <FakeScreen appKey={appKey} tick={tick} />
              {showBoxes && data.detects.map(d => (
                <div key={d.id}
                  className="absolute border border-accent/70 rounded-sm"
                  style={{ left: `${d.x}%`, top: `${d.y}%`, width: `${d.w}%`, height: `${d.h}%` }}>
                  <span className="absolute -top-3 left-0 text-[8px] font-mono uppercase tracking-wider text-accent bg-background/80 px-1 rounded-sm">
                    {d.kind} · {d.conf}
                  </span>
                </div>
              ))}
              {showOcr && (
                <div className="absolute inset-x-0 bottom-0 p-2 bg-gradient-to-t from-background/95 to-transparent">
                  <p className="font-mono text-[9px] text-accent uppercase tracking-wider">OCR · {data.detects.filter(d => d.kind === "text").length} text regions</p>
                </div>
              )}
            </div>
          </PhoneFrame>
        </div>

        <aside className="border-l hairline px-6 py-6 space-y-6">
          <div>
            <p className="text-[9px] uppercase tracking-[0.22em] text-accent">Mirroring</p>
            <p className="mt-1 font-display text-[18px]">{phone?.name ?? "Phone"}</p>
            <p className="text-[10px] text-muted-foreground">{data.app} · {data.screen}</p>
          </div>

          <div>
            <p className="text-[9px] uppercase tracking-[0.22em] text-muted-foreground mb-2">App</p>
            <div className="grid grid-cols-3 gap-px rounded-md overflow-hidden border hairline bg-[var(--color-border)]">
              {(Object.keys(APPS) as (keyof typeof APPS)[]).map(k => (
                <button key={k} onClick={() => setAppKey(k)}
                  className={`px-2 py-1.5 text-[10px] capitalize ${appKey === k ? "bg-accent text-accent-foreground" : "bg-background text-muted-foreground"}`}>
                  {k}
                </button>
              ))}
            </div>
          </div>

          <Toggle label="Bounding boxes" value={showBoxes} onChange={setShowBoxes} />
          <Toggle label="OCR overlay" value={showOcr} onChange={setShowOcr} />

          <div>
            <p className="text-[9px] uppercase tracking-[0.22em] text-muted-foreground mb-2">Zoom</p>
            <input type="range" min={0.7} max={1.4} step={0.05} value={zoom}
              onChange={e => setZoom(parseFloat(e.target.value))}
              className="w-full accent-[color:var(--color-accent)]" />
            <p className="text-[10px] text-muted-foreground mt-1">{zoom.toFixed(2)}×</p>
          </div>

          <div>
            <p className="text-[9px] uppercase tracking-[0.22em] text-muted-foreground mb-2">Actions</p>
            <div className="space-y-1.5 text-[11px]">
              <button onClick={() => setTick(x => x + 1)} className="w-full text-left px-2 py-1.5 rounded hover:bg-surface">Refresh frame</button>
              <button className="w-full text-left px-2 py-1.5 rounded hover:bg-surface">Take screenshot</button>
              <button className="w-full text-left px-2 py-1.5 rounded hover:bg-surface">Fullscreen mirror</button>
            </div>
          </div>

          <div>
            <p className="text-[9px] uppercase tracking-[0.22em] text-muted-foreground mb-2">Detected ({data.detects.length})</p>
            <ul className="space-y-1 text-[11px]">
              {data.detects.map(d => (
                <li key={d.id} className="flex items-center justify-between gap-2">
                  <span className="flex items-center gap-2 truncate">
                    <span className="font-mono text-[9px] uppercase text-accent">{d.kind}</span>
                    <span className="truncate">{d.label}</span>
                  </span>
                  <span className="font-mono text-[9px] text-muted-foreground">{d.conf}%</span>
                </li>
              ))}
            </ul>
          </div>
        </aside>
      </div>
    </Shell>
  );
}

export function PhoneFrame({ zoom = 1, children }: { zoom?: number; children: React.ReactNode }) {
  return (
    <div
      className="relative rounded-[36px] border-2 border-[color:var(--color-border-strong)] bg-background shadow-2xl"
      style={{ width: 260 * zoom, height: 540 * zoom, transition: "all 200ms ease" }}
    >
      <div className="absolute inset-2 rounded-[28px] overflow-hidden">{children}</div>
      <div className="absolute top-2 left-1/2 -translate-x-1/2 w-20 h-3 rounded-full bg-background border hairline" />
    </div>
  );
}

function FakeScreen({ appKey, tick }: { appKey: string; tick: number }) {
  return (
    <div className="absolute inset-0 grain">
      <div className="absolute top-0 inset-x-0 h-6 flex items-center justify-between px-3 text-[9px] font-mono text-muted-foreground border-b hairline">
        <span>9:41</span>
        <span className="capitalize">{appKey}</span>
        <span>72%</span>
      </div>
      <div className="absolute top-6 inset-x-0 bottom-0 p-3 text-[10px] text-muted-foreground">
        <p className="font-display text-[14px] text-foreground capitalize">{appKey}</p>
        <p className="mt-1">Frame #{tick}</p>
      </div>
    </div>
  );
}

function Toggle({ label, value, onChange }: { label: string; value: boolean; onChange: (v: boolean) => void }) {
  return (
    <button onClick={() => onChange(!value)} className="w-full flex items-center justify-between text-[12px]">
      <span>{label}</span>
      <span className={`h-4 w-7 rounded-full border hairline relative transition ${value ? "bg-accent" : "bg-surface"}`}>
        <span className={`absolute top-[1px] h-[12px] w-[12px] rounded-full bg-background transition ${value ? "left-[13px]" : "left-[1px]"}`} />
      </span>
    </button>
  );
}
