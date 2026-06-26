import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useEffect, useState, useRef } from "react";
import { ApaOrb } from "@/components/apa/ApaOrb";
import { ParticleField } from "@/components/apa/ParticleField";
import { useEnt } from "@/lib/apa/enterprise";

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: "APA-OS — Artificial Personal Assistant Operating System" },
      { name: "description", content: "An operating layer above your apps. State outcomes, not workflows." },
    ],
  }),
  component: IndexPage,
});

const SERVICES = [
  "Initializing memory engine",
  "Connecting device bridge",
  "Loading knowledge graph",
  "Activating agent swarm",
  "Calibrating world model",
  "Syncing digital twin",
  "Preparing outcome orchestrator",
];

function IndexPage() {
  const authenticated = useEnt((s) => s.authenticated);

  if (!authenticated) {
    return <SplashPage />;
  }

  return <InlineConsole />;
}

/* ────────────────────────────────────────────
   Splash Screen — only for first-time visitors
   ──────────────────────────────────────────── */
function SplashPage() {
  const navigate = useNavigate();
  const [progress, setProgress] = useState(0);
  const [serviceIdx, setServiceIdx] = useState(0);
  const [phase, setPhase] = useState<"entering" | "loading" | "ready" | "exiting">("entering");
  const intervalRef = useRef<ReturnType<typeof setInterval>>(null);

  useEffect(() => {
    const t = setTimeout(() => setPhase("loading"), 800);
    return () => clearTimeout(t);
  }, []);

  useEffect(() => {
    if (phase !== "loading") return;
    intervalRef.current = setInterval(() => {
      setServiceIdx((i) => {
        if (i >= SERVICES.length - 1) {
          clearInterval(intervalRef.current!);
          setProgress(100);
          setPhase("ready");
          return i;
        }
        return i + 1;
      });
      setProgress((p) => Math.min(p + 100 / SERVICES.length, 100));
    }, 400);
    return () => clearInterval(intervalRef.current!);
  }, [phase]);

  useEffect(() => {
    if (phase !== "ready") return;
    const t = setTimeout(() => {
      setPhase("exiting");
      setTimeout(() => navigate({ to: "/login" }), 600);
    }, 1200);
    return () => clearTimeout(t);
  }, [phase, navigate]);

  return (
    <div className={`fixed inset-0 z-50 flex flex-col items-center justify-center bg-background overflow-hidden transition-opacity duration-500 ${phase === "exiting" ? "opacity-0" : "opacity-100"}`}>
      <div className="absolute inset-0 gradient-mesh" />
      <ParticleField count={60} speed={0.2} opacity={0.3} />
      <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
        <div className="w-[500px] h-[500px] rounded-full" style={{ background: "radial-gradient(circle, oklch(0.78 0.11 70 / 0.08) 0%, transparent 70%)" }} />
      </div>

      <div className="relative z-10 flex flex-col items-center gap-8">
        <div className={`transition-all duration-1000 ${phase === "entering" ? "opacity-0 scale-75 blur-sm" : "opacity-100 scale-100 blur-0"}`}>
          <ApaOrb size={100} state={phase === "ready" ? "success" : phase === "loading" ? "thinking" : "idle"} />
        </div>
        <div className={`text-center transition-all duration-700 ${phase === "entering" ? "opacity-0 translate-y-4" : "opacity-100 translate-y-0"}`} style={{ transitionDelay: "200ms" }}>
          <h1 className="font-display text-[52px] md:text-[64px] tracking-tight leading-none">
            APA<span className="text-accent">-</span>OS
          </h1>
          <p className="mt-3 text-[11px] md:text-[13px] uppercase tracking-[0.35em] text-muted-foreground">
            Artificial Personal Assistant Operating System
          </p>
        </div>
        <div className={`flex flex-col items-center gap-4 transition-all duration-500 ${phase === "entering" ? "opacity-0" : "opacity-100"}`} style={{ transitionDelay: "500ms" }}>
          <div className="w-[240px] h-[2px] bg-[var(--color-border)] rounded-full overflow-hidden">
            <div className="h-full bg-accent rounded-full transition-all duration-300 ease-out" style={{ width: `${progress}%` }} />
          </div>
          <p className="font-mono text-[10px] uppercase tracking-[0.2em] text-muted-foreground h-4">
            {phase === "loading" && (
              <span className="apa-fade-up inline-block">
                {SERVICES[serviceIdx]}
                <span className="inline-block w-[3px] h-[10px] bg-accent ml-1 animate-[blink_1s_step-end_infinite]" />
              </span>
            )}
            {phase === "ready" && (
              <span className="text-[color:var(--color-success)] inline-block apa-fade-up">All systems ready</span>
            )}
          </p>
        </div>
        <div className={`flex items-center gap-6 mt-4 transition-all duration-500 ${phase === "entering" ? "opacity-0" : "opacity-100"}`} style={{ transitionDelay: "700ms" }}>
          {["Memory", "Agents", "Devices", "Knowledge"].map((label, i) => (
            <div key={label} className="flex items-center gap-2">
              <span className={`h-1.5 w-1.5 rounded-full transition-colors duration-300 ${
                serviceIdx > i * 2 || phase === "ready" ? "bg-[color:var(--color-success)]"
                : serviceIdx === i * 2 ? "bg-accent apa-pulse"
                : "bg-muted-foreground/30"
              }`} />
              <span className="text-[9px] uppercase tracking-[0.18em] text-muted-foreground/70">{label}</span>
            </div>
          ))}
        </div>
      </div>

      <div className="absolute bottom-8 left-0 right-0 flex justify-center">
        <p className={`text-[9px] uppercase tracking-[0.25em] text-muted-foreground/40 transition-all duration-500 ${phase === "entering" ? "opacity-0" : "opacity-100"}`} style={{ transitionDelay: "900ms" }}>
          v3 · Calm Intelligence · {new Date().getFullYear()}
        </p>
      </div>
      <style>{`@keyframes blink { 0%, 100% { opacity: 1; } 50% { opacity: 0; } }`}</style>
    </div>
  );
}

/* ────────────────────────────────────────────
   Console — inline to avoid lazy-import issues
   ──────────────────────────────────────────── */
import { Shell } from "@/components/apa/Shell";
import { useApa } from "@/lib/apa/store";
import { AGENTS } from "@/lib/apa/agents";
import { runOutcome, STAGE_LABEL } from "@/lib/apa/orchestrator";
import type { Outcome, StageKey, AgentMessage } from "@/lib/apa/types";

const SUGGESTIONS = [
  "Help me prepare for tomorrow",
  "Open Instagram",
  "Send the attendance screenshot to Deepak",
  "Help me pass this semester",
  "Find my ATM Protocol notes",
  "Plan my next week",
];

const TABS = ["Outcome", "Device", "Research", "Memory", "Automation"] as const;
type Tab = typeof TABS[number];

function InlineConsole() {
  const [text, setText] = useState("");
  const [running, setRunning] = useState(false);
  const [tab, setTab] = useState<Tab>("Outcome");
  const outcomes = useApa(s => s.outcomes);
  const focused = outcomes[0];
  const inputRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => { inputRef.current?.focus(); }, []);

  async function submit() {
    const t = text.trim();
    if (!t || running) return;
    setRunning(true);
    setText("");
    try { await runOutcome(t); } finally {
      setRunning(false);
      setTimeout(() => inputRef.current?.focus(), 0);
    }
  }

  return (
    <Shell>
      <section className="px-10 pt-14 pb-8 border-b hairline">
        <div className="flex items-baseline justify-between">
          <p className="text-[11px] uppercase tracking-[0.28em] text-accent">Command surface</p>
          <div className="flex gap-px rounded-md overflow-hidden border hairline bg-[var(--color-border)]">
            {TABS.map(t => (
              <button key={t} onClick={() => setTab(t)}
                className={["px-3 py-1 text-[11px] tracking-wide transition", tab === t ? "bg-accent text-accent-foreground" : "bg-background text-muted-foreground hover:text-foreground"].join(" ")}
              >{t}</button>
            ))}
          </div>
        </div>
        <h1 className="mt-5 font-display text-[56px] leading-[0.98] tracking-tight max-w-3xl">
          What would you like<span className="block text-muted-foreground">to be true?</span>
        </h1>
        <p className="mt-5 max-w-xl text-[14px] leading-relaxed text-muted-foreground">
          Speak naturally. The system will determine goals, plans, devices, memories, agents, and actions automatically.
        </p>
        <div className="mt-9 max-w-3xl">
          <div className="rounded-xl border hairline-strong bg-surface/60 backdrop-blur p-5 glow-ochre">
            <textarea ref={inputRef} value={text} onChange={e => setText(e.target.value)}
              onKeyDown={e => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); submit(); } }}
              rows={2}
              placeholder={tab === "Device" ? "Open Instagram · Mirror phone · Send screenshot…" : tab === "Research" ? "Find ATM Protocol notes · Compare DBMS vs OS…" : tab === "Memory" ? "What did Deepak send me? · When did I last study Networks?" : tab === "Automation" ? "Every morning at 8:30 AM ping me with…" : "What would you like to be true?"}
              className="w-full resize-none bg-transparent text-lg font-display tracking-tight outline-none placeholder:text-muted-foreground/50"
            />
            <div className="mt-3 flex items-center justify-between">
              <div className="flex items-center gap-4 text-[10px] text-muted-foreground">
                <span className="flex items-center gap-2"><span className="h-1.5 w-1.5 rounded-full bg-accent apa-pulse" />10 agents ready</span>
                <span className="hidden sm:inline">·</span>
                <span className="hidden sm:inline">5 devices connected</span>
                <span className="hidden md:inline">·</span>
                <span className="hidden md:inline">memory active · prediction engine online</span>
              </div>
              <div className="flex items-center gap-2">
                <button title="Voice" className="h-7 w-7 rounded-md border hairline text-muted-foreground hover:text-accent hover:border-accent transition text-[12px]">●</button>
                <button title="Upload" className="h-7 w-7 rounded-md border hairline text-muted-foreground hover:text-accent hover:border-accent transition text-[12px]">+</button>
                <button title="Camera" className="h-7 w-7 rounded-md border hairline text-muted-foreground hover:text-accent hover:border-accent transition text-[12px]">◎</button>
                <button onClick={submit} disabled={!text.trim() || running}
                  className="rounded-md bg-accent px-4 py-1.5 text-[12px] font-medium text-accent-foreground transition disabled:opacity-40 hover:brightness-110">
                  {running ? "Orchestrating…" : "Run  ↵"}
                </button>
              </div>
            </div>
          </div>
          <div className="mt-5 flex flex-wrap gap-2">
            {SUGGESTIONS.map(s => (
              <button key={s} onClick={() => setText(s)}
                className="rounded-full border hairline px-3 py-1.5 text-[11.5px] text-muted-foreground hover:text-foreground hover:border-accent transition">{s}</button>
            ))}
          </div>
        </div>
      </section>
      {focused ? <MissionControl outcome={focused} /> : (
        <section className="px-10 py-16">
          <p className="text-sm text-muted-foreground italic max-w-xl">Nothing in flight. The system is quietly watching your portal, inbox, and calendar.</p>
        </section>
      )}
    </Shell>
  );
}

const STAGES: StageKey[] = ["intent","agents","memory","world","predictions","plan","execution","complete"];

function MissionControl({ outcome }: { outcome: Outcome }) {
  return (
    <section className="px-10 py-9">
      <ol className="flex flex-wrap gap-px mb-9 rounded-md overflow-hidden border hairline bg-[var(--color-border)]">
        {STAGES.map(s => {
          const idx = STAGES.indexOf(s);
          const cur = STAGES.indexOf(outcome.currentStage);
          const done = idx < cur;
          const active = idx === cur;
          return (
            <li key={s} className={["flex-1 min-w-[120px] bg-background px-3 py-2 text-[10px] uppercase tracking-[0.18em]", done ? "text-success" : active ? "text-accent" : "text-muted-foreground/60"].join(" ")}>
              <span className="block font-mono">{String(idx + 1).padStart(2,"0")}</span>
              <span>{STAGE_LABEL[s]}</span>
              {active && <span className="block mt-1 h-[2px] bg-accent apa-stream rounded" />}
            </li>
          );
        })}
      </ol>
      <div className="mb-10">
        <p className="mb-3 text-[10px] uppercase tracking-[0.22em] text-muted-foreground">Outcome analysis</p>
        <div className="grid grid-cols-2 md:grid-cols-5 gap-px bg-[var(--color-border)] border hairline">
          <div className="bg-background p-4 md:col-span-1"><p className="font-mono text-[9.5px] uppercase tracking-[0.18em] text-muted-foreground">Intent</p><p className="mt-1.5 text-[13px] font-display leading-snug">{outcome.text}</p></div>
          <div className="bg-background p-4"><p className="font-mono text-[9.5px] uppercase tracking-[0.18em] text-muted-foreground">Category</p><p className="mt-1.5 text-[13px]">{outcome.category}</p></div>
          <div className="bg-background p-4"><p className="font-mono text-[9.5px] uppercase tracking-[0.18em] text-muted-foreground">Priority</p><p className="mt-1.5 text-[13px] text-accent capitalize">{outcome.priority}</p></div>
          <div className="bg-background p-4"><p className="font-mono text-[9.5px] uppercase tracking-[0.18em] text-muted-foreground">Confidence</p><p className="mt-1.5 text-[13px] text-accent">{outcome.confidence}%</p></div>
          <div className="bg-background p-4"><p className="font-mono text-[9.5px] uppercase tracking-[0.18em] text-muted-foreground">Duration</p><p className="mt-1.5 text-[13px]">{outcome.duration}</p></div>
        </div>
      </div>
      <div className="mb-10">
        <p className="mb-3 text-[10px] uppercase tracking-[0.22em] text-muted-foreground">Agent activation</p>
        <ul className="grid grid-cols-2 md:grid-cols-5 gap-px bg-[var(--color-border)] border hairline">
          {outcome.agents.map(a => {
            const meta = AGENTS[a.agentId];
            return (
              <li key={a.agentId} className="bg-background p-4">
                <p className="font-mono text-[10px] uppercase tracking-[0.18em] text-muted-foreground">{a.status}</p>
                <p className="mt-1 text-[13px]">{meta.name.replace(" Agent", "")}</p>
                <p className="mt-0.5 text-[10.5px] text-muted-foreground line-clamp-2">{meta.role}</p>
                {a.confidence && <p className="mt-2 font-mono text-[10px] text-accent">conf {a.confidence}%</p>}
              </li>
            );
          })}
        </ul>
      </div>
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-px bg-[var(--color-border)] border hairline mb-10">
        <div className="bg-background p-5"><p className="text-[10px] uppercase tracking-[0.22em] text-accent">Memory recall</p><div className="mt-3">{outcome.memoryRecall.length === 0 ? <div className="space-y-2 py-2"><span className="block h-[2px] w-full bg-[var(--color-border)] rounded apa-stream" /><p className="font-mono text-[10px] uppercase tracking-wider text-muted-foreground">awaiting…</p></div> : <ul className="space-y-2.5">{outcome.memoryRecall.map((it, i) => <li key={i} className="flex items-baseline justify-between gap-4 apa-fade-up"><span className="font-mono text-[10px] uppercase tracking-wider text-muted-foreground shrink-0">{it.label}</span><span className="text-[12.5px] text-right">{it.value}</span></li>)}</ul>}</div></div>
        <div className="bg-background p-5"><p className="text-[10px] uppercase tracking-[0.22em] text-accent">World model</p><div className="mt-3">{outcome.worldContext.length === 0 ? <div className="space-y-2 py-2"><span className="block h-[2px] w-full bg-[var(--color-border)] rounded apa-stream" /><p className="font-mono text-[10px] uppercase tracking-wider text-muted-foreground">awaiting…</p></div> : <ul className="space-y-2.5">{outcome.worldContext.map((it, i) => <li key={i} className="flex items-baseline justify-between gap-4 apa-fade-up"><span className="font-mono text-[10px] uppercase tracking-wider text-muted-foreground shrink-0">{it.label}</span><span className="text-[12.5px] text-right">{it.value}</span></li>)}</ul>}</div></div>
        <div className="bg-background p-5"><p className="text-[10px] uppercase tracking-[0.22em] text-accent">Predictions</p><div className="mt-3">{outcome.predictions.length === 0 ? <div className="space-y-2 py-2"><span className="block h-[2px] w-full bg-[var(--color-border)] rounded apa-stream" /><p className="font-mono text-[10px] uppercase tracking-wider text-muted-foreground">awaiting…</p></div> : <ul className="space-y-3">{outcome.predictions.map((p, i) => <li key={i}><div className="flex items-baseline justify-between"><span className="text-[12.5px]">{p.label}</span><span className="font-mono text-[11px] text-accent">{p.value}%</span></div><div className="mt-1 h-[2px] bg-[var(--color-border)] rounded overflow-hidden"><div className="h-full bg-accent" style={{ width: `${p.value}%` }} /></div>{p.delta !== undefined && <p className={`mt-1 text-[10px] ${p.delta >= 0 ? "text-success" : "text-warn"}`}>{p.delta >= 0 ? "+" : ""}{p.delta}% vs baseline</p>}</li>)}</ul>}</div></div>
      </div>
      <div className="grid grid-cols-1 lg:grid-cols-[1.1fr_1.1fr_1fr] gap-px bg-[var(--color-border)] border hairline mb-10">
        <div className="bg-background p-5"><p className="text-[10px] uppercase tracking-[0.22em] text-accent">Execution plan</p><div className="mt-3"><ol className="space-y-3">{outcome.plan.map((step, i) => <li key={step.id} className="flex items-baseline gap-3"><span className="font-mono text-[10px] text-muted-foreground w-5 shrink-0">{i+1}</span><div><p className="text-[13px]">{step.title}</p><p className="text-[11.5px] text-muted-foreground">{step.detail}</p><p className="mt-1 font-mono text-[9.5px] uppercase tracking-wider text-muted-foreground/70">{step.when} · via {step.agent}</p></div></li>)}</ol></div></div>
        <div className="bg-background p-5"><p className="text-[10px] uppercase tracking-[0.22em] text-accent">Live execution</p><div className="mt-3">{outcome.executionLog.length === 0 ? <div className="space-y-2 py-2"><span className="block h-[2px] w-full bg-[var(--color-border)] rounded apa-stream" /><p className="font-mono text-[10px] uppercase tracking-wider text-muted-foreground">awaiting…</p></div> : <ol className="relative border-l hairline-strong pl-5 space-y-3">{outcome.executionLog.map((l, i) => <li key={i} className="relative apa-fade-up"><span className="absolute -left-[26px] top-1.5 h-2 w-2 rounded-full bg-success" /><p className="font-mono text-[9.5px] uppercase tracking-wider text-muted-foreground">{new Date(l.at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" })} · {l.agent}</p><p className="mt-0.5 text-[13px]">✓ {l.label}</p></li>)}</ol>}</div></div>
        <div className="bg-background p-5"><p className="text-[10px] uppercase tracking-[0.22em] text-accent">Agent conversation</p><div className="mt-3">{outcome.conversation.length === 0 ? <div className="space-y-2 py-2"><span className="block h-[2px] w-full bg-[var(--color-border)] rounded apa-stream" /><p className="font-mono text-[10px] uppercase tracking-wider text-muted-foreground">awaiting…</p></div> : <ul className="space-y-2.5 max-h-[280px] overflow-y-auto pr-1">{outcome.conversation.map((m, i) => <li key={i} className="apa-fade-up"><p className="font-mono text-[9.5px] uppercase tracking-wider text-accent">{AGENTS[m.from].name.replace(" Agent","")}{m.to && <span className="text-muted-foreground"> → {AGENTS[m.to].name.replace(" Agent","")}</span>}</p><p className="text-[12.5px] leading-snug text-foreground/90">{m.text}</p></li>)}</ul>}</div></div>
      </div>
      <div className="mb-10">
        <p className="mb-3 text-[10px] uppercase tracking-[0.22em] text-muted-foreground">Recommended next actions</p>
        <ul className="flex flex-wrap gap-2">
          {outcome.nextActions.map((a, i) => (
            <li key={i}><button className="rounded-md border hairline-strong bg-surface/40 px-4 py-2 text-left hover:border-accent transition group"><p className="text-[13px]">{a.label}</p><p className="font-mono text-[10px] text-muted-foreground group-hover:text-accent">{a.impact ?? "one click"} {a.minutes ? `· ${a.minutes} min` : ""}</p></button></li>
          ))}
        </ul>
      </div>
    </section>
  );
}
