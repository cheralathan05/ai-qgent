import { createFileRoute } from "@tanstack/react-router";
import { useState } from "react";
import { Shell, PageHeader, Section } from "@/components/apa/Shell";

export const Route = createFileRoute("/screen-analysis")({
  head: () => ({ meta: [{ title: "Screen Analysis — APA-OS" }] }),
  component: AnalysisPage,
});

const SAMPLES = [
  {
    id: "ig-feed",     app: "Instagram", screen: "Feed",      classification: "Social feed",
    nav: ["Home > Feed"], actions: ["Like", "Comment", "Share", "Open DM"],
    tree: [
      { id: "root", label: "FeedScrollView", children: [
        { id: "p1", label: "Post · @deepak", children: [
          { id: "img", label: "Image" },
          { id: "act", label: "ActionBar" },
        ]},
        { id: "p2", label: "Post · @nikhil" },
      ]},
    ],
  },
  {
    id: "ig-dm",       app: "Instagram", screen: "DM thread", classification: "Direct messaging",
    nav: ["Home > Inbox > Thread · Deepak"], actions: ["Reply", "Voice note", "Send media", "React"],
    tree: [{ id: "root", label: "ChatScroll", children: [{ id: "input", label: "MessageInput" }] }],
  },
  {
    id: "wa-chat",     app: "WhatsApp",  screen: "Chat",      classification: "Direct messaging",
    nav: ["Chats > Guru Chat"], actions: ["Reply", "Attach", "Voice"],
    tree: [{ id: "root", label: "ChatContainer", children: [{ id: "msgs", label: "MessagesList" }, { id: "in", label: "InputBar" }] }],
  },
  {
    id: "settings",    app: "Settings",  screen: "Root",      classification: "System preferences",
    nav: ["Settings"], actions: ["Open Wi-Fi", "Open Display", "Open Battery"],
    tree: [{ id: "root", label: "SettingsList", children: [{ id: "wifi", label: "Wi-Fi" }, { id: "bt", label: "Bluetooth" }] }],
  },
  {
    id: "chrome",      app: "Chrome",    screen: "Search",    classification: "Browser",
    nav: ["Tab · new"], actions: ["Search", "Open tab", "Voice search"],
    tree: [{ id: "root", label: "Tab", children: [{ id: "url", label: "OmniBox" }] }],
  },
];

function AnalysisPage() {
  const [id, setId] = useState(SAMPLES[0].id);
  const s = SAMPLES.find(x => x.id === id)!;

  return (
    <Shell>
      <PageHeader
        eyebrow="Phase 02 · Understanding"
        title="Screen Analysis."
        lede="Not just see — understand. The current screen, what app, what navigation state, what's visible, what the user can do."
      />

      <div className="px-7 py-5 border-t hairline flex flex-wrap gap-2">
        {SAMPLES.map(sm => (
          <button key={sm.id} onClick={() => setId(sm.id)}
            className={`text-[11px] px-3 py-1.5 rounded-full border hairline transition
              ${id === sm.id ? "border-accent text-accent bg-accent/5" : "text-muted-foreground hover:text-foreground"}`}>
            {sm.app} · {sm.screen}
          </button>
        ))}
      </div>

      <Section title="Classification">
        <div className="grid sm:grid-cols-4 gap-5">
          <Stat label="App" value={s.app} />
          <Stat label="Screen" value={s.screen} />
          <Stat label="Classification" value={s.classification} accent />
          <Stat label="Confidence" value="98%" />
        </div>
      </Section>

      <Section title="Navigation state">
        <ul className="space-y-2 text-[13px]">
          {s.nav.map((n, i) => (
            <li key={i} className="font-mono text-[12px] text-muted-foreground">{n}</li>
          ))}
        </ul>
      </Section>

      <Section title="Visible actions">
        <div className="flex flex-wrap gap-2">
          {s.actions.map(a => (
            <span key={a} className="text-[11px] px-3 py-1.5 rounded-full border hairline text-foreground">{a}</span>
          ))}
        </div>
      </Section>

      <Section title="Layout tree">
        <Tree nodes={s.tree} depth={0} />
      </Section>
    </Shell>
  );
}

function Tree({ nodes, depth }: { nodes: any[]; depth: number }) {
  return (
    <ul className="space-y-1">
      {nodes.map(n => (
        <li key={n.id}>
          <div className="font-mono text-[11.5px] flex gap-2" style={{ paddingLeft: depth * 16 }}>
            <span className="text-muted-foreground">{depth === 0 ? "▸" : "·"}</span>
            <span>{n.label}</span>
          </div>
          {n.children && <Tree nodes={n.children} depth={depth + 1} />}
        </li>
      ))}
    </ul>
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
