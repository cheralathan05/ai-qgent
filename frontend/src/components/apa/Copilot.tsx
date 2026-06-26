import { useEffect, useRef, useState } from "react";
import { entStore, useEnt, pushActivity } from "@/lib/apa/enterprise";
import { useApa } from "@/lib/apa/store";
import { useRouterState } from "@tanstack/react-router";

interface Msg { id: string; from: "you" | "copilot"; text: string; at: number; }

const PAGE_HINTS: Record<string, string> = {
  "/":            "You're in the Outcome Console. State a goal and I'll orchestrate the agent floor.",
  "/agents":      "This is the Agent Command Center — 10 internal agents, their roles and runs.",
  "/goals":       "Goal Orchestrator — break goals into pillars; I'll simulate next best actions.",
  "/world":       "World Model — your context graph. Click any node to see its reasoning paths.",
  "/timeline":    "Unified Activity Timeline — commands, devices, knowledge, workflows in one stream.",
  "/devices":     "Live Device Center — mirrored screens, vision overlays, execution verification.",
  "/replay":      "Execution Replay — scrub through every action taken on your behalf.",
  "/memory":      "Memory Evolution — what the system has learned about you over time.",
  "/errors":      "Global Error Center — failures, recovery suggestions, retries.",
  "/audit":       "Audit Center — every action, with user, source, result.",
  "/system":      "System Health — backend, database, queues, devices.",
  "/notifications": "Notification inbox — categorised, searchable.",
};

const QUICK = [
  "Explain this screen",
  "What should I do next?",
  "Find my ATM Protocol notes",
  "Analyze the last failure",
  "Summarize today",
];

export function CopilotDrawer() {
  const open = useEnt(s => s.prefs.copilotOpen);
  const pathname = useRouterState({ select: s => s.location.pathname });
  const outcomes = useApa(s => s.outcomes);
  const focused = outcomes[0];

  const [msgs, setMsgs] = useState<Msg[]>([]);
  const [input, setInput] = useState("");
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => { endRef.current?.scrollIntoView({ behavior: "smooth" }); }, [msgs]);

  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if ((e.metaKey || e.ctrlKey) && e.key === "/") {
        e.preventDefault();
        entStore.set(s => ({ ...s, prefs: { ...s.prefs, copilotOpen: !s.prefs.copilotOpen } }));
      }
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  function send(text: string) {
    const t = text.trim();
    if (!t) return;
    const you: Msg = { id: crypto.randomUUID(), from: "you", text: t, at: Date.now() };
    setMsgs(m => [...m, you]);
    setInput("");
    pushActivity({ kind: "command", title: `Copilot · ${t}` });
    setTimeout(() => {
      const ctx = PAGE_HINTS[pathname] ?? "I have full context of this page.";
      const focusLine = focused ? ` Current outcome: "${focused.text}" — stage ${focused.currentStage}.` : "";
      const reply: Msg = {
        id: crypto.randomUUID(), from: "copilot", at: Date.now(),
        text: synthesize(t, ctx + focusLine),
      };
      setMsgs(m => [...m, reply]);
    }, 480);
  }

  if (!open) return null;

  return (
    <aside
      role="complementary"
      aria-label="AI Copilot"
      className="fixed right-0 top-0 z-40 h-screen w-[380px] max-w-[92vw] border-l hairline-strong bg-background/95 backdrop-blur flex flex-col"
    >
      <header className="flex items-center justify-between px-5 py-4 border-b hairline">
        <div>
          <p className="text-[9px] uppercase tracking-[0.22em] text-accent">Copilot</p>
          <p className="text-[12px] text-muted-foreground mt-0.5">Context-aware · ⌘/ to toggle</p>
        </div>
        <button
          onClick={() => entStore.set(s => ({ ...s, prefs: { ...s.prefs, copilotOpen: false } }))}
          aria-label="Close Copilot"
          className="text-muted-foreground hover:text-foreground text-sm"
        >✕</button>
      </header>

      <div className="px-5 py-3 border-b hairline text-[11.5px] text-muted-foreground leading-relaxed">
        {PAGE_HINTS[pathname] ?? "I have context of this page."}
      </div>

      <div className="flex-1 overflow-y-auto px-5 py-4 space-y-3">
        {msgs.length === 0 && (
          <div className="space-y-2">
            <p className="text-[10px] uppercase tracking-[0.22em] text-muted-foreground">Try</p>
            {QUICK.map(q => (
              <button
                key={q}
                onClick={() => send(q)}
                className="block w-full text-left text-[12.5px] px-3 py-2 rounded-md border hairline hover:bg-surface/60 transition"
              >{q}</button>
            ))}
          </div>
        )}
        {msgs.map(m => (
          <div key={m.id} className={m.from === "you" ? "text-right" : ""}>
            <div className={[
              "inline-block max-w-[90%] px-3 py-2 rounded-lg text-[12.5px] leading-relaxed",
              m.from === "you"
                ? "bg-accent text-accent-foreground"
                : "bg-surface text-foreground border hairline"
            ].join(" ")}>{m.text}</div>
          </div>
        ))}
        <div ref={endRef} />
      </div>

      <form
        onSubmit={e => { e.preventDefault(); send(input); }}
        className="border-t hairline p-3 flex gap-2"
      >
        <input
          value={input}
          onChange={e => setInput(e.target.value)}
          placeholder="Ask Copilot…"
          aria-label="Message Copilot"
          className="flex-1 bg-surface rounded-md px-3 py-2 text-[12.5px] outline-none border hairline focus:border-accent"
        />
        <button className="px-3 py-2 rounded-md bg-accent text-accent-foreground text-[12px] font-medium">Send</button>
      </form>
    </aside>
  );
}

function synthesize(q: string, ctx: string): string {
  const ql = q.toLowerCase();
  if (ql.includes("explain")) return `${ctx} The active layer maps directly to the layer in the sidebar — every signal you see here is live state.`;
  if (ql.includes("next"))    return `Next best action: focus the Compilers Unit 4 revision block at 8 PM. ${ctx}`;
  if (ql.includes("find"))    return `Pulled 3 candidates from your knowledge sources. Top hit: "ATM Protocol Notes.pdf" in Drive › College › Sem 5.`;
  if (ql.includes("fail") || ql.includes("error"))
    return `Last failure: brief WebSocket drop to the iPhone bridge. Auto-recovered in 3s. No data lost. Recovery path: retry · backoff · resume stream.`;
  if (ql.includes("summar"))  return `Today: 4 agent runs, 2 device actions, 1 approval, 0 errors. Calm day.`;
  return `Acknowledged. ${ctx}`;
}
