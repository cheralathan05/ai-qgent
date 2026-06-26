import { createFileRoute } from "@tanstack/react-router";
import { useEffect, useMemo, useRef, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { Shell } from "@/components/apa/Shell";
import { useApa } from "@/lib/apa/store";
import { runOutcome } from "@/lib/apa/orchestrator";
import { pushActivity, useEnt } from "@/lib/apa/enterprise";
import { AGENTS } from "@/lib/apa/agents";
import type { AgentId, StageKey } from "@/lib/apa/types";

export const Route = createFileRoute("/assistant")({
  head: () => ({ meta: [{ title: "Assistant — APA-OS" }] }),
  component: AssistantPage,
});

/* ────────────────────────── types ────────────────────────── */

type OrbState =
  | "idle" | "listening" | "thinking" | "executing"
  | "speaking" | "success" | "warning" | "error";

interface Turn {
  id: string;
  role: "user" | "apa";
  text: string;
  at: number;
  outcomeId?: string;
  streaming?: boolean;
}

const STAGE_LABEL: Record<StageKey, string> = {
  intent:      "Understanding request",
  agents:      "Selecting agents",
  memory:      "Recalling memory",
  world:       "Reading world",
  predictions: "Forecasting",
  plan:        "Creating plan",
  execution:   "Executing",
  complete:    "Completed",
};
const STAGE_ORDER: StageKey[] = [
  "intent","agents","memory","world","predictions","plan","execution","complete",
];

const SUGGESTIONS = [
  "Open Instagram",
  "Help me prepare for tomorrow",
  "Send the attendance screenshot to Deepak",
  "Find my ATM Protocol notes",
  "What's my battery?",
  "Continue Compilers revision",
];

function greet() {
  const h = new Date().getHours();
  if (h < 5)  return "Still up,";
  if (h < 12) return "Good morning,";
  if (h < 17) return "Good afternoon,";
  if (h < 21) return "Good evening,";
  return "Good night,";
}

/* ────────────────────────── page ────────────────────────── */

function AssistantPage() {
  const outcomes = useApa(s => s.outcomes);
  const devices  = useApa(s => s.devices);
  const memory   = useApa(s => s.memory);
  const activity = useEnt(s => s.activity);

  const focused = outcomes[0];

  const [turns, setTurns] = useState<Turn[]>([]);
  const [input, setInput] = useState("");
  const [orb, setOrb]     = useState<OrbState>("idle");
  const [wake, setWake]   = useState(true);
  const [continuous, setContinuous] = useState(false);
  const [contextOpen, setContextOpen] = useState(true);
  const [deviceId, setDeviceId] = useState(devices.find(d => d.kind === "phone")?.id ?? devices[0]?.id);
  const [holding, setHolding] = useState(false);

  const endRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  /* keep textarea focused */
  useEffect(() => { inputRef.current?.focus(); }, []);
  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [turns.length, focused?.currentStage]);

  /* map orchestrator → orb state */
  useEffect(() => {
    if (!focused) { setOrb(holding ? "listening" : "idle"); return; }
    const m: Record<StageKey, OrbState> = {
      intent: "thinking", agents: "thinking", memory: "thinking",
      world: "thinking", predictions: "thinking",
      plan: "thinking", execution: "executing", complete: "success",
    };
    setOrb(m[focused.currentStage]);
    if (focused.currentStage === "complete") {
      const key = focused.id + ":done";
      setTurns(t => t.some(x => x.id === key) ? t : ([
        ...t,
        { id: key, role: "apa", at: Date.now(), outcomeId: focused.id,
          text: speakReply(focused.text, focused.plan[0]?.title, focused.nextActions[0]?.label) },
      ]));
      const tm = setTimeout(() => setOrb("idle"), 2200);
      return () => clearTimeout(tm);
    }
  }, [focused?.currentStage, focused?.id, holding]);

  async function send(text: string) {
    const t = text.trim();
    if (!t) return;
    setInput("");
    const id = crypto.randomUUID();
    setTurns(prev => [...prev, { id, role: "user", text: t, at: Date.now() }]);
    pushActivity({ kind: "command", title: `Assistant · ${t}` });
    setOrb("thinking");
    await runOutcome(t);
    requestAnimationFrame(() => inputRef.current?.focus());
  }

  const targetDevice = devices.find(d => d.id === deviceId) ?? devices[0];

  return (
    <Shell>
      <div className="flex flex-col h-[calc(100vh-3.25rem)]">
        {/* Status strip */}
        <StatusStrip
          orb={orb}
          device={targetDevice?.name ?? "—"}
          memoryCount={memory.length}
          connected={(targetDevice?.status === "connected") || (targetDevice?.status === "controlling")}
          onToggleContext={() => setContextOpen(o => !o)}
          contextOpen={contextOpen}
        />

        <div className="grid grid-cols-1 lg:grid-cols-[1fr_360px] flex-1 min-h-0 border-t hairline">
          {/* Conversation column */}
          <section className="flex flex-col min-h-0 relative">
            <div className="flex-1 overflow-y-auto px-4 sm:px-8 py-8">
              {turns.length === 0 ? (
                <Welcome onPick={send} />
              ) : (
                <div className="max-w-[760px] mx-auto space-y-7">
                  {turns.map(turn => (
                    <TurnRow key={turn.id} turn={turn} outcomes={outcomes} />
                  ))}
                  {focused && focused.currentStage !== "complete" && (
                    <ExecutionCard outcome={focused} />
                  )}
                  <div ref={endRef} />
                </div>
              )}
            </div>

            {/* Composer */}
            <Composer
              input={input}
              setInput={setInput}
              onSend={() => send(input)}
              onHoldStart={() => { setHolding(true); setOrb("listening"); }}
              onHoldEnd={() => {
                setHolding(false);
                if (orb === "listening") setOrb("idle");
              }}
              orb={orb}
              inputRef={inputRef}
            />
          </section>

          {/* Context rail */}
          <AnimatePresence initial={false}>
            {contextOpen && (
              <motion.aside
                key="ctx"
                initial={{ opacity: 0, x: 24 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: 24 }}
                transition={{ type: "spring", stiffness: 220, damping: 28 }}
                className="hidden lg:flex flex-col border-l hairline min-h-0"
              >
                <ContextRail
                  device={targetDevice}
                  devices={devices}
                  onDevice={setDeviceId}
                  wake={wake} setWake={setWake}
                  continuous={continuous} setContinuous={setContinuous}
                  focused={focused}
                  activity={activity}
                  memory={memory}
                  onPick={send}
                />
              </motion.aside>
            )}
          </AnimatePresence>
        </div>
      </div>
    </Shell>
  );
}

/* ────────────────────────── Status strip ────────────────────────── */

function StatusStrip({
  orb, device, memoryCount, connected, onToggleContext, contextOpen,
}: {
  orb: OrbState; device: string; memoryCount: number; connected: boolean;
  onToggleContext: () => void; contextOpen: boolean;
}) {
  return (
    <header className="h-14 grid grid-cols-[1fr_auto_1fr] items-center px-4 sm:px-7 gap-4 bg-background/85 backdrop-blur">
      <div className="flex items-center gap-6 min-w-0">
        <StatusPill label="Assistant" value={orb} tone={orbTone(orb)} />
        <StatusPill label="Device" value={device} />
        <StatusPill label="Memory" value={`${memoryCount} notes · live`} />
      </div>

      <div className="flex items-center gap-3">
        <span className={`h-1.5 w-1.5 rounded-full ${connected ? "bg-[color:var(--color-success)]" : "bg-warn"} apa-pulse`} />
        <p className="font-mono text-[10px] uppercase tracking-[0.22em] text-muted-foreground">
          {connected ? "Realtime · linked" : "Offline · queued"}
        </p>
      </div>

      <div className="flex items-center justify-end gap-2">
        <button
          onClick={onToggleContext}
          className="text-[10px] uppercase tracking-[0.22em] px-2.5 py-1 rounded border hairline text-muted-foreground hover:text-foreground hidden lg:inline-flex"
        >{contextOpen ? "Hide context" : "Show context"}</button>
      </div>
    </header>
  );
}

function StatusPill({ label, value, tone }: { label: string; value: string; tone?: string }) {
  return (
    <div className="min-w-0">
      <p className="text-[9px] uppercase tracking-[0.22em] text-muted-foreground">{label}</p>
      <p className={`text-[12px] truncate ${tone ?? "text-foreground"}`}>{value}</p>
    </div>
  );
}

function orbTone(s: OrbState) {
  switch (s) {
    case "executing": case "thinking": case "listening": return "text-accent";
    case "success": return "text-[color:var(--color-success)]";
    case "warning": return "text-warn";
    case "error":   return "text-destructive";
    default:        return "text-foreground";
  }
}

/* ────────────────────────── Welcome ────────────────────────── */

function Welcome({ onPick }: { onPick: (s: string) => void }) {
  return (
    <div className="max-w-[760px] mx-auto pt-16">
      <motion.div
        initial={{ opacity: 0, y: 18 }} animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6, ease: "easeOut" }}
        className="flex flex-col items-center text-center"
      >
        <Orb state="idle" size={132} />
        <p className="mt-10 text-[11px] uppercase tracking-[0.32em] text-accent">{greet()}</p>
        <h1 className="mt-3 font-display text-[44px] sm:text-[56px] leading-[1.02] tracking-tight">
          Cheralathan.
        </h1>
        <p className="mt-3 text-[14px] text-muted-foreground max-w-md">
          State an outcome. I'll choose the agents, devices, and steps. You don't have to think about apps.
        </p>
      </motion.div>

      <motion.div
        initial="hidden" animate="show"
        variants={{ show: { transition: { staggerChildren: 0.05, delayChildren: 0.25 } } }}
        className="mt-14 grid sm:grid-cols-2 gap-2.5"
      >
        {SUGGESTIONS.map(s => (
          <motion.button
            key={s}
            variants={{ hidden: { opacity: 0, y: 10 }, show: { opacity: 1, y: 0 } }}
            onClick={() => onPick(s)}
            className="group text-left px-4 py-3.5 rounded-lg border hairline hover:border-[color:var(--color-border-strong)] hover:bg-surface/60 transition flex items-center justify-between gap-4"
          >
            <span className="text-[13px]">{s}</span>
            <span className="text-[10px] uppercase tracking-[0.22em] text-muted-foreground opacity-0 group-hover:opacity-100 transition">
              run ↵
            </span>
          </motion.button>
        ))}
      </motion.div>
    </div>
  );
}

/* ────────────────────────── Turn / Execution ────────────────────────── */

function TurnRow({ turn, outcomes }: { turn: Turn; outcomes: ReturnType<typeof useApa<any>> }) {
  const isUser = turn.role === "user";
  const outcome = turn.outcomeId ? outcomes.find((o: any) => o.id === turn.outcomeId) : undefined;
  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35 }}
      className={`flex gap-4 ${isUser ? "justify-end" : "justify-start"}`}
    >
      {!isUser && <Orb state={outcome?.currentStage === "complete" ? "success" : "speaking"} size={32} compact />}
      <div className={`max-w-[78%] ${isUser ? "text-right" : ""}`}>
        <p className="text-[9px] uppercase tracking-[0.22em] text-muted-foreground mb-1.5">
          {isUser ? "You" : "APA"} · {new Date(turn.at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
        </p>
        <div className={[
          "inline-block rounded-2xl px-4 py-3 text-[14.5px] leading-relaxed border hairline",
          isUser ? "bg-surface" : "bg-background",
        ].join(" ")}>{turn.text}</div>
      </div>
      {isUser && <span className="h-8 w-8 shrink-0 rounded-full border hairline grid place-items-center text-[10px] text-muted-foreground">C</span>}
    </motion.div>
  );
}

function ExecutionCard({ outcome }: { outcome: any }) {
  const stages = STAGE_ORDER;
  const currentIdx = stages.indexOf(outcome.currentStage);
  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }}
      className="ml-12 rounded-2xl border hairline-strong bg-surface/40 overflow-hidden"
    >
      <div className="px-5 py-4 border-b hairline flex items-center justify-between">
        <div className="min-w-0">
          <p className="text-[9px] uppercase tracking-[0.22em] text-accent">Live execution</p>
          <p className="mt-1 font-display text-[16px] truncate">{outcome.text}</p>
        </div>
        <div className="text-right">
          <p className="text-[10px] uppercase tracking-[0.22em] text-muted-foreground">{outcome.category}</p>
          <p className="text-[10px] text-muted-foreground mt-0.5">conf {outcome.confidence}%</p>
        </div>
      </div>

      {/* Stage timeline */}
      <ol className="px-5 py-4 space-y-2">
        {stages.map((s, i) => {
          const done = i < currentIdx || outcome.currentStage === "complete";
          const active = i === currentIdx && outcome.currentStage !== "complete";
          return (
            <li key={s} className="grid grid-cols-[14px_1fr_auto] items-center gap-3 text-[12px]">
              <span className={[
                "h-2.5 w-2.5 rounded-full transition",
                done ? "bg-[color:var(--color-success)]"
                  : active ? "bg-accent apa-pulse"
                  : "bg-muted-foreground/25",
              ].join(" ")} />
              <span className={done ? "text-foreground" : active ? "text-foreground" : "text-muted-foreground/70"}>
                {STAGE_LABEL[s]}
              </span>
              <span className="font-mono text-[9px] uppercase tracking-wider text-muted-foreground">
                {done ? "ok" : active ? "…" : ""}
              </span>
            </li>
          );
        })}
      </ol>

      {/* Agents row */}
      <div className="px-5 py-3 border-t hairline flex flex-wrap gap-1.5">
        {outcome.agents.map((a: any) => (
          <span key={a.agentId}
            className={[
              "text-[10px] px-2 py-0.5 rounded-full border hairline",
              a.status === "done"    ? "text-[color:var(--color-success)] border-[color:var(--color-success)]/40"
                : a.status === "running" ? "text-accent border-accent/40 apa-pulse"
                : a.status === "queued"  ? "text-muted-foreground"
                : "text-muted-foreground/70",
            ].join(" ")}>
            {AGENTS[a.agentId as AgentId]?.name.replace(" Agent", "") ?? a.agentId}
          </span>
        ))}
      </div>

      {/* Execution log */}
      {outcome.executionLog?.length > 0 && (
        <ul className="px-5 py-3 border-t hairline space-y-1.5 max-h-44 overflow-y-auto">
          {outcome.executionLog.slice(-6).map((l: any, i: number) => (
            <li key={i} className="grid grid-cols-[64px_1fr_auto] gap-3 text-[11px] font-mono">
              <span className="text-muted-foreground">
                {new Date(l.at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" })}
              </span>
              <span className="font-sans text-[12px]">{l.label}</span>
              <span className={l.status === "ok" ? "text-[color:var(--color-success)]" : l.status === "warn" ? "text-warn" : "text-muted-foreground"}>
                {l.status}
              </span>
            </li>
          ))}
        </ul>
      )}

      {/* Next actions */}
      {outcome.currentStage === "complete" && outcome.nextActions?.length > 0 && (
        <div className="px-5 py-3 border-t hairline flex flex-wrap gap-2">
          {outcome.nextActions.slice(0, 4).map((n: any) => (
            <button key={n.label}
              className="text-[11px] px-2.5 py-1 rounded-full border hairline hover:border-accent hover:text-accent transition">
              {n.label}{n.impact ? ` · ${n.impact}` : ""}
            </button>
          ))}
        </div>
      )}
    </motion.div>
  );
}

/* ────────────────────────── Composer ────────────────────────── */

function Composer({
  input, setInput, onSend, onHoldStart, onHoldEnd, orb, inputRef,
}: {
  input: string; setInput: (s: string) => void; onSend: () => void;
  onHoldStart: () => void; onHoldEnd: () => void; orb: OrbState;
  inputRef: React.RefObject<HTMLTextAreaElement | null>;
}) {
  return (
    <div className="border-t hairline bg-background/85 backdrop-blur px-4 sm:px-8 py-4">
      <div className="max-w-[760px] mx-auto">
        <div className="flex items-end gap-3">
          <button
            onMouseDown={onHoldStart} onMouseUp={onHoldEnd}
            onMouseLeave={(e) => { if ((e.buttons & 1) === 0) return; onHoldEnd(); }}
            onTouchStart={onHoldStart} onTouchEnd={onHoldEnd}
            aria-label="Push to talk"
            className="shrink-0"
          >
            <Orb state={orb} size={52} interactive />
          </button>

          <div className="flex-1 rounded-2xl border hairline bg-surface/60 focus-within:border-accent transition">
            <textarea
              ref={inputRef}
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={e => {
                if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); onSend(); }
              }}
              rows={1}
              placeholder="Tell me what to do… ⏎ to send, Shift+⏎ for new line"
              className="block w-full resize-none bg-transparent px-4 pt-3 pb-1 text-[14.5px] leading-relaxed outline-none placeholder:text-muted-foreground/50"
              style={{ minHeight: 44, maxHeight: 180 }}
            />
            <div className="flex items-center justify-between px-3 pb-2 pt-1">
              <div className="flex items-center gap-1">
                <ToolBtn label="Attach" icon="paperclip" />
                <ToolBtn label="Camera" icon="camera" />
                <ToolBtn label="Screen" icon="screen" />
                <ToolBtn label="Command" icon="command" />
              </div>
              <button
                onClick={onSend}
                disabled={!input.trim()}
                className="text-[10px] uppercase tracking-[0.22em] px-3 py-1.5 rounded-md bg-accent text-accent-foreground disabled:opacity-30 disabled:cursor-not-allowed"
              >Send ↵</button>
            </div>
          </div>
        </div>

        <p className="mt-2 text-center text-[10px] uppercase tracking-[0.22em] text-muted-foreground/70">
          {orb === "listening" ? "Listening… release to send" :
           orb === "thinking" ? "Thinking through your request" :
           orb === "executing" ? "Executing on your devices" :
           "Hold orb to speak · ⌘K for command center"}
        </p>
      </div>
    </div>
  );
}

function ToolBtn({ label, icon }: { label: string; icon: string }) {
  return (
    <button
      title={label}
      className="h-8 w-8 grid place-items-center rounded-md text-muted-foreground hover:text-foreground hover:bg-background/60 transition"
    >
      <Icon name={icon} />
    </button>
  );
}

function Icon({ name }: { name: string }) {
  const c = "h-3.5 w-3.5";
  switch (name) {
    case "paperclip": return (<svg className={c} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6"><path d="M21 12.5 12.5 21a5 5 0 0 1-7-7L14 5.5a3.5 3.5 0 0 1 5 5L10.5 19a2 2 0 0 1-3-3l8-8"/></svg>);
    case "camera":    return (<svg className={c} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6"><path d="M3 8h3l2-2h8l2 2h3v11H3z"/><circle cx="12" cy="13" r="3.5"/></svg>);
    case "screen":    return (<svg className={c} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6"><rect x="3" y="4" width="18" height="13" rx="2"/><path d="M8 21h8M12 17v4"/></svg>);
    case "command":   return (<svg className={c} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6"><path d="M9 6a3 3 0 1 0-3 3h12a3 3 0 1 0-3-3v12a3 3 0 1 0 3-3H6a3 3 0 1 0 3 3z"/></svg>);
    default: return null;
  }
}

/* ────────────────────────── Context rail ────────────────────────── */

function ContextRail({
  device, devices, onDevice, wake, setWake, continuous, setContinuous,
  focused, activity, memory, onPick,
}: any) {
  return (
    <div className="flex-1 overflow-y-auto px-6 py-7 space-y-8">
      {/* Now */}
      <section>
        <p className="text-[9px] uppercase tracking-[0.22em] text-accent">Now</p>
        <div className="mt-3 rounded-xl border hairline p-4 space-y-2.5">
          <Row k="Device" v={device?.name ?? "—"} />
          <Row k="Status" v={device?.status ?? "—"} tone={device?.status === "connected" ? "success" : "muted"} />
          <Row k="Battery" v={device?.battery ? `${device.battery}%` : "—"} />
          <Row k="App" v={focused?.category === "Device control" ? focused.text : "Home"} />
          <Row k="Screen" v={focused ? "observed" : "—"} />
          <Row k="Network" v="5G · 220ms" />
        </div>
      </section>

      {/* Target device */}
      <section>
        <p className="text-[9px] uppercase tracking-[0.22em] text-muted-foreground">Target device</p>
        <ul className="mt-2 space-y-1">
          {devices.map((d: any) => (
            <li key={d.id}>
              <label className="flex items-center gap-2 cursor-pointer text-[12px] py-1">
                <input type="radio" name="targetDev" className="accent-[color:var(--color-accent)]"
                  checked={device?.id === d.id} onChange={() => onDevice(d.id)} />
                <span className="flex-1 truncate">{d.name}</span>
                <span className="font-mono text-[9px] uppercase tracking-wider text-muted-foreground">{d.status}</span>
              </label>
            </li>
          ))}
        </ul>
      </section>

      {/* Voice */}
      <section>
        <p className="text-[9px] uppercase tracking-[0.22em] text-muted-foreground">Voice</p>
        <div className="mt-3 space-y-3">
          <Toggle label="Wake word · 'Hey APA'" value={wake} onChange={setWake} />
          <Toggle label="Continuous listening" value={continuous} onChange={setContinuous} />
        </div>
      </section>

      {/* Active workflow */}
      {focused && (
        <section>
          <p className="text-[9px] uppercase tracking-[0.22em] text-muted-foreground">Active workflow</p>
          <div className="mt-3 rounded-xl border hairline p-4">
            <p className="font-display text-[14px] leading-snug">{focused.text}</p>
            <p className="mt-1 text-[10px] text-muted-foreground">
              {focused.category} · stage {focused.currentStage}
            </p>
            <div className="mt-3 h-[2px] bg-[var(--color-border)] rounded overflow-hidden">
              <div className="h-full bg-accent transition-all"
                style={{ width: `${((STAGE_ORDER.indexOf(focused.currentStage)+1)/STAGE_ORDER.length)*100}%` }} />
            </div>
          </div>
        </section>
      )}

      {/* Proactive */}
      <section>
        <p className="text-[9px] uppercase tracking-[0.22em] text-muted-foreground">Suggested</p>
        <div className="mt-2 space-y-1">
          {SUGGESTIONS.slice(0, 4).map(s => (
            <button key={s} onClick={() => onPick(s)}
              className="block w-full text-left text-[12px] px-3 py-2 rounded-md border hairline hover:bg-surface/60 transition">
              {s}
            </button>
          ))}
        </div>
      </section>

      {/* Recent */}
      <section>
        <p className="text-[9px] uppercase tracking-[0.22em] text-muted-foreground">Recent</p>
        <ul className="mt-2 space-y-1.5">
          {activity.slice(0, 6).map((a: any) => (
            <li key={a.id} className="grid grid-cols-[1fr_auto] items-baseline gap-3 text-[11.5px]">
              <span className="truncate">{a.title}</span>
              <span className="font-mono text-[9px] text-muted-foreground uppercase tracking-wider">{a.kind}</span>
            </li>
          ))}
        </ul>
      </section>

      {/* Memory */}
      <section>
        <p className="text-[9px] uppercase tracking-[0.22em] text-muted-foreground">Remembers</p>
        <ul className="mt-2 space-y-1.5">
          {memory.slice(0, 4).map((m: any) => (
            <li key={m.id} className="text-[11.5px] leading-snug">
              <span className="font-mono text-[9px] uppercase tracking-wider text-accent mr-2">{m.kind}</span>
              <span className="text-foreground/85">{m.text}</span>
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}

function Row({ k, v, tone }: { k: string; v: string; tone?: "success" | "muted" }) {
  const color =
    tone === "success" ? "text-[color:var(--color-success)]" :
    tone === "muted"   ? "text-muted-foreground" : "text-foreground";
  return (
    <div className="flex items-baseline justify-between text-[12px]">
      <span className="text-muted-foreground">{k}</span>
      <span className={color}>{v}</span>
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

/* ────────────────────────── Animated Orb ────────────────────────── */

function Orb({ state, size = 96, compact = false, interactive = false }: {
  state: OrbState; size?: number; compact?: boolean; interactive?: boolean;
}) {
  const color =
    state === "executing" || state === "thinking" || state === "listening" || state === "speaking"
      ? "var(--color-accent)"
    : state === "success" ? "var(--color-success)"
    : state === "warning" ? "var(--color-warn)"
    : state === "error"   ? "var(--color-destructive)"
    : "var(--color-border-strong)";

  const intensity =
    state === "listening" ? 1
    : state === "executing" ? 0.9
    : state === "thinking" ? 0.7
    : state === "speaking" ? 0.85
    : state === "idle" ? 0.25 : 0.6;

  // gentle rotation while thinking/executing
  const rotating = state === "thinking" || state === "executing";

  return (
    <div
      className={["relative grid place-items-center", interactive ? "cursor-pointer" : ""].join(" ")}
      style={{ width: size, height: size }}
    >
      {/* outer halo */}
      <motion.span
        className="absolute inset-0 rounded-full"
        style={{
          background: `radial-gradient(circle at 50% 50%, color-mix(in oklab, ${color} 35%, transparent) 0%, transparent 65%)`,
        }}
        animate={{ opacity: [intensity * 0.6, intensity, intensity * 0.6] }}
        transition={{ duration: 2.4, repeat: Infinity, ease: "easeInOut" }}
      />
      {/* rotating ring */}
      {rotating && (
        <motion.span
          className="absolute rounded-full border-2"
          style={{
            inset: 4,
            borderColor: color,
            borderTopColor: "transparent",
            opacity: 0.55,
          }}
          animate={{ rotate: 360 }}
          transition={{ duration: state === "executing" ? 2.2 : 3.4, repeat: Infinity, ease: "linear" }}
        />
      )}
      {/* core */}
      <motion.span
        className="rounded-full border-2 bg-background/70 backdrop-blur grid place-items-center"
        style={{
          width: size * 0.62, height: size * 0.62,
          borderColor: color,
          boxShadow: `0 0 ${size * 0.55}px -${size * 0.18}px ${color}`,
        }}
        animate={
          state === "listening"
            ? { scale: [1, 1.08, 1] }
          : state === "speaking"
            ? { scale: [1, 1.05, 0.97, 1.04, 1] }
          : state === "success"
            ? { scale: [1, 1.15, 1] }
          : { scale: 1 }
        }
        transition={
          state === "listening" ? { duration: 1.1, repeat: Infinity, ease: "easeInOut" }
          : state === "speaking" ? { duration: 1.6, repeat: Infinity, ease: "easeInOut" }
          : { duration: 0.6 }
        }
      >
        {!compact && (
          <span
            className="h-2 w-2 rounded-full"
            style={{ background: color, boxShadow: `0 0 18px ${color}` }}
          />
        )}
      </motion.span>

      {/* waveform when listening / speaking */}
      {(state === "listening" || state === "speaking") && !compact && (
        <Waveform color={color} size={size} />
      )}
    </div>
  );
}

function Waveform({ color, size }: { color: string; size: number }) {
  const bars = useMemo(() => Array.from({ length: 14 }, (_, i) => i), []);
  return (
    <div
      className="absolute flex items-end gap-[2px]"
      style={{ bottom: -size * 0.22, height: size * 0.14 }}
    >
      {bars.map(i => (
        <motion.span
          key={i}
          className="w-[2px] rounded-full"
          style={{ background: color }}
          animate={{ height: ["20%", "100%", "30%", "80%", "20%"] }}
          transition={{
            duration: 1 + (i % 3) * 0.18,
            repeat: Infinity,
            ease: "easeInOut",
            delay: i * 0.05,
          }}
        />
      ))}
    </div>
  );
}

/* ────────────────────────── helpers ────────────────────────── */

function speakReply(text: string, first?: string, next?: string) {
  const t = text.toLowerCase();
  if (t.includes("battery"))    return "Your phone battery is at 72% on iPhone, connected via the device bridge.";
  if (t.includes("instagram"))  return "Instagram is open and verified on your iPhone. I'm watching the screen — say the word for the next step.";
  if (t.includes("whatsapp"))   return "WhatsApp is ready. Tell me who to message.";
  if (t.includes("tomorrow") || t.includes("prepare"))
    return "I've built tomorrow's plan around your 8–10 PM focus window. Compilers Unit 4 first, mock test ready, Deepak pinged.";
  if (first) return `${first}. ${next ?? "What's next?"}`;
  return "Done. What would you like next?";
}
