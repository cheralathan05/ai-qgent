import { createFileRoute, Link } from "@tanstack/react-router";
import { useState } from "react";
import { Shell, PageHeader, Section } from "@/components/apa/Shell";

export const Route = createFileRoute("/knowledge-connect")({
  head: () => ({ meta: [{ title: "Connect Knowledge — APA-OS" }] }),
  component: KnowledgeConnectPage,
});

const PROVIDERS = ["Google Drive", "OneDrive", "GitHub", "GitLab", "Notion", "Dropbox", "Google Calendar"];

function KnowledgeConnectPage() {
  const [picked, setPicked] = useState<Set<string>>(new Set(["Google Drive", "GitHub", "Notion"]));
  function toggle(p: string) {
    setPicked(s => { const n = new Set(s); n.has(p) ? n.delete(p) : n.add(p); return n; });
  }

  return (
    <Shell>
      <PageHeader
        eyebrow="Onboarding · 4"
        title="Connect your knowledge."
        lede="Plug in the places your work already lives. APA reads, embeds, and remembers — privately."
      />

      <Section title="Sources">
        <ul className="grid sm:grid-cols-2 gap-3">
          {PROVIDERS.map(p => {
            const on = picked.has(p);
            return (
              <li key={p}>
                <button onClick={() => toggle(p)}
                  className={`w-full text-left border rounded-md p-4 transition ${on ? "border-accent bg-surface/40" : "hairline hover:border-foreground/40"}`}>
                  <div className="flex items-center justify-between">
                    <p className="font-display text-[15px]">{p}</p>
                    <span className={`text-[10px] uppercase tracking-[0.22em] ${on ? "text-accent" : "text-muted-foreground"}`}>
                      {on ? "connected" : "connect"}
                    </span>
                  </div>
                </button>
              </li>
            );
          })}
        </ul>
      </Section>

      <div className="px-7 py-6 border-t hairline flex justify-between items-center">
        <Link to="/onboarding" className="text-[10px] uppercase tracking-[0.22em] text-muted-foreground hover:text-foreground">Skip</Link>
        <Link to="/device-connect" className="px-4 py-2.5 border hairline-strong rounded-md text-[11px] uppercase tracking-[0.22em] hover:text-accent hover:border-accent">
          Continue →
        </Link>
      </div>
    </Shell>
  );
}
