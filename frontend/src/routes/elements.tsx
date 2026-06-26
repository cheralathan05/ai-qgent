import { createFileRoute } from "@tanstack/react-router";
import { useState } from "react";
import { Shell, PageHeader, Section } from "@/components/apa/Shell";

export const Route = createFileRoute("/elements")({
  head: () => ({ meta: [{ title: "Visual Elements — APA-OS" }] }),
  component: ElementsPage,
});

type Kind = "button" | "input" | "menu" | "tab" | "icon" | "label";

interface Element { id: string; kind: Kind; label: string; x: number; y: number; w: number; h: number; conf: number; app: string }

const ALL: Element[] = [
  { id: "e1", kind: "icon",  label: "Search",   app: "WhatsApp",  x: 8,  y: 6,  w: 8,  h: 5,  conf: 98 },
  { id: "e2", kind: "icon",  label: "Camera",   app: "WhatsApp",  x: 84, y: 6,  w: 8,  h: 5,  conf: 95 },
  { id: "e3", kind: "label", label: "Deepak",   app: "WhatsApp",  x: 18, y: 22, w: 40, h: 4,  conf: 99 },
  { id: "e4", kind: "button",label: "New chat", app: "WhatsApp",  x: 78, y: 88, w: 14, h: 8,  conf: 96 },
  { id: "e5", kind: "tab",   label: "Chats",    app: "WhatsApp",  x: 0,  y: 14, w: 25, h: 5,  conf: 99 },
  { id: "e6", kind: "tab",   label: "Status",   app: "WhatsApp",  x: 25, y: 14, w: 25, h: 5,  conf: 99 },
  { id: "e7", kind: "input", label: "Search",   app: "Settings",  x: 8,  y: 8,  w: 84, h: 5,  conf: 95 },
  { id: "e8", kind: "menu",  label: "Wi-Fi",    app: "Settings",  x: 8,  y: 18, w: 60, h: 5,  conf: 99 },
  { id: "e9", kind: "icon",  label: "Like",     app: "Instagram", x: 6,  y: 64, w: 8,  h: 5,  conf: 94 },
  { id: "e10",kind: "icon",  label: "Comment",  app: "Instagram", x: 16, y: 64, w: 8,  h: 5,  conf: 94 },
  { id: "e11",kind: "label", label: "@deepak",  app: "Instagram", x: 12, y: 18, w: 30, h: 4,  conf: 97 },
  { id: "e12",kind: "button",label: "Send",     app: "Instagram", x: 80, y: 92, w: 14, h: 6,  conf: 93 },
];

const KINDS: { id: Kind | "all"; label: string }[] = [
  { id: "all", label: "All" },
  { id: "button", label: "Buttons" },
  { id: "input", label: "Inputs" },
  { id: "menu", label: "Menus" },
  { id: "tab", label: "Tabs" },
  { id: "icon", label: "Icons" },
  { id: "label", label: "Labels" },
];

function ElementsPage() {
  const [filter, setFilter] = useState<Kind | "all">("all");
  const [q, setQ] = useState("");
  const items = ALL.filter(e =>
    (filter === "all" || e.kind === filter) &&
    (!q || e.label.toLowerCase().includes(q.toLowerCase()) || e.app.toLowerCase().includes(q.toLowerCase()))
  );

  return (
    <Shell>
      <PageHeader
        eyebrow="Phase 02 · Vision"
        title="Visual Elements."
        lede="Every detected button, input, menu, tab, icon, and label across the live phone — with coordinates and confidence."
      />

      <div className="px-7 py-5 border-t hairline flex flex-wrap items-center gap-3">
        {KINDS.map(k => (
          <button key={k.id} onClick={() => setFilter(k.id)}
            className={`text-[11px] px-3 py-1.5 rounded-full border hairline transition
              ${filter === k.id ? "border-accent text-accent bg-accent/5" : "text-muted-foreground hover:text-foreground"}`}>
            {k.label}
          </button>
        ))}
        <span className="flex-1" />
        <input
          value={q}
          onChange={e => setQ(e.target.value)}
          placeholder="Filter…"
          className="bg-surface border hairline rounded px-3 py-1.5 text-[12px] outline-none placeholder:text-muted-foreground/50 w-48"
        />
      </div>

      <Section title={`${items.length} detected`}>
        <div className="overflow-x-auto">
          <table className="w-full text-[12.5px]">
            <thead>
              <tr className="text-left border-b hairline">
                {["Kind", "Label", "App", "x", "y", "w", "h", "Confidence"].map(h => (
                  <th key={h} className="py-2.5 pr-4 text-[9px] uppercase tracking-[0.22em] text-muted-foreground font-normal">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {items.map(e => (
                <tr key={e.id} className="border-b hairline hover:bg-surface/50 transition">
                  <td className="py-2.5 pr-4"><span className="font-mono text-[10px] uppercase text-accent">{e.kind}</span></td>
                  <td className="py-2.5 pr-4">{e.label}</td>
                  <td className="py-2.5 pr-4 text-muted-foreground">{e.app}</td>
                  <td className="py-2.5 pr-4 font-mono text-[11px] text-muted-foreground">{e.x}%</td>
                  <td className="py-2.5 pr-4 font-mono text-[11px] text-muted-foreground">{e.y}%</td>
                  <td className="py-2.5 pr-4 font-mono text-[11px] text-muted-foreground">{e.w}%</td>
                  <td className="py-2.5 pr-4 font-mono text-[11px] text-muted-foreground">{e.h}%</td>
                  <td className="py-2.5 pr-4">
                    <div className="flex items-center gap-2">
                      <div className="h-1 w-20 rounded-full bg-[var(--color-border)]">
                        <div className="h-full rounded-full bg-accent" style={{ width: `${e.conf}%` }} />
                      </div>
                      <span className="font-mono text-[10px] text-muted-foreground">{e.conf}%</span>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Section>
    </Shell>
  );
}
