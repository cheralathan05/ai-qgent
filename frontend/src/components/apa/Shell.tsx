import { Link, useRouter, useRouterState } from "@tanstack/react-router";
import { useCallback, useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import { useApa, apaStore } from "@/lib/apa/store";
import { AGENTS } from "@/lib/apa/agents";
import { runOutcome } from "@/lib/apa/orchestrator";
import type { AgentId, AgentStatus, AutonomyMode } from "@/lib/apa/types";
import { TopBar } from "./TopBar";
import { StatusBar } from "./StatusBar";
import { CopilotDrawer } from "./Copilot";
import { useEnt, pushActivity, logoutUser } from "@/lib/apa/enterprise";
import { SignOutModal, SignOutAnimation, SignOutButton } from "./SignOut";

const NAV = [
  { to: "/",            label: "Console",      hint: "Outcomes" },
  { to: "/dashboard",   label: "Dashboard",    hint: "Overview" },
  { to: "/assistant",   label: "Assistant",    hint: "Voice · live" },
  { to: "/console",     label: "Commands",     hint: "Text console" },
  { to: "/workflows",   label: "Workflows",    hint: "Live runs" },
  { to: "/events",      label: "Events",       hint: "Realtime feed" },
  { to: "/approvals",   label: "Approvals",    hint: "Pending consent" },
  { to: "/screen",      label: "Screen",       hint: "Phone mirror" },
  { to: "/screen-analysis", label: "Analysis", hint: "Understand UI" },
  { to: "/screen-intelligence", label: "Screen IQ", hint: "Detected · parsed" },
  { to: "/screen-memory", label: "Screen Memory", hint: "Visual history" },
  { to: "/phone-intelligence", label: "Phone IQ", hint: "State · history" },
  { to: "/navigation",  label: "Navigation",   hint: "Known paths" },
  { to: "/elements",    label: "Elements",     hint: "Detected UI" },
  { to: "/app-knowledge", label: "App Knowledge", hint: "Known apps" },
  { to: "/verification",label: "Verification", hint: "Evidence" },
  { to: "/knowledge",   label: "Knowledge",    hint: "Files · docs" },
  { to: "/knowledge/search", label: "Search",  hint: "Semantic" },
  { to: "/knowledge/sources", label: "Sources",hint: "Drive · GitHub" },
  { to: "/knowledge/graph", label: "Graph",    hint: "Connections" },
  { to: "/knowledge/chat", label: "RAG Chat",  hint: "Ask · cited" },
  { to: "/life",        label: "Life",         hint: "Long horizons" },
  { to: "/future-self", label: "Future Self",  hint: "Trajectory" },
  { to: "/career",      label: "Career",       hint: "Readiness" },
  { to: "/learning",    label: "Learning",     hint: "Sprints" },
  { to: "/projects",    label: "Projects",     hint: "Shipping" },
  { to: "/reality",     label: "Reality",      hint: "Time vs intent" },
  { to: "/agents",      label: "Agents",       hint: "Mission control" },
  { to: "/agents/monitor", label: "Agent Monitor", hint: "Health · latency" },
  { to: "/research",    label: "Research",     hint: "Long tasks" },
  { to: "/automations", label: "Automations",  hint: "Triggers · rules" },
  { to: "/organization",label: "Organization", hint: "Autonomous org" },
  { to: "/goals",       label: "Goals",        hint: "Orchestrator" },
  { to: "/world",       label: "World",        hint: "Live model" },
  { to: "/twin",        label: "Twin",         hint: "You, simulated" },
  { to: "/timeline",    label: "Timeline",     hint: "Activity stream" },
  { to: "/predictions", label: "Predictions",  hint: "Risk & readiness" },
  { to: "/memory",      label: "Memory",       hint: "What it learned" },
  { to: "/devices",     label: "Devices",      hint: "Live control" },
  { to: "/device-connect", label: "Pair Device", hint: "QR · onboarding" },
  { to: "/mobile-agent",label: "Mobile Agent", hint: "APK status" },
  { to: "/knowledge-connect", label: "Connect Sources", hint: "Onboarding" },
  { to: "/replay",      label: "Replay",       hint: "Every action" },
  { to: "/trust",       label: "Trust",        hint: "Why it acted" },
  { to: "/observatory", label: "Observatory",  hint: "Live execution" },
  { to: "/brain",       label: "Second Brain", hint: "Recall" },
  { to: "/employee",    label: "Employee",     hint: "Autonomous mode" },
  { to: "/emergency",   label: "Emergency",    hint: "Copilot mode" },
  { to: "/notifications", label: "Inbox",      hint: "Notifications" },
  { to: "/errors",      label: "Errors",       hint: "Failures · recovery" },
  { to: "/audit",       label: "Audit",        hint: "Every action" },
  { to: "/system",      label: "Health",       hint: "System status" },
  { to: "/workspaces",  label: "Workspaces",   hint: "Personal · Study" },
  { to: "/profile",     label: "Profile",      hint: "You" },
  { to: "/settings",    label: "Settings",     hint: "Flags · personalize" },
] as const;


export function Shell({ children }: { children: ReactNode }) {
  const pathname = useRouterState({ select: s => s.location.pathname });
  const [cmdOpen, setCmdOpen] = useState(false);
  const [signOutModalOpen, setSignOutModalOpen] = useState(false);
  const [signOutAnimating, setSignOutAnimating] = useState(false);
  const router = useRouter();

  const handleSignOutConfirm = useCallback(() => {
    setSignOutModalOpen(false);
    setSignOutAnimating(true);
  }, []);

  const handleSignOutAnimationDone = useCallback(() => {
    logoutUser();
    setSignOutAnimating(false);
    router.navigate({ to: "/login" });
  }, [router]);

  // ⌘K / Ctrl+K  + double-space voice
  useEffect(() => {
    let lastSpace = 0;
    function onKey(e: KeyboardEvent) {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setCmdOpen(o => !o);
      }
      if (e.key === " " && (e.target as HTMLElement)?.tagName !== "TEXTAREA"
          && (e.target as HTMLElement)?.tagName !== "INPUT") {
        const now = Date.now();
        if (now - lastSpace < 320) {
          e.preventDefault();
          setCmdOpen(true);
        }
        lastSpace = now;
      }
      if (e.key === "Escape") setCmdOpen(false);
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  return (
    <div className="min-h-screen bg-background text-foreground grain pb-7">
      <TopBar />
      <div className="mx-auto grid max-w-[1680px] grid-cols-[240px_1fr_300px] gap-0">
        <Sidebar pathname={pathname} onSignOut={() => setSignOutModalOpen(true)} />
        <main id="main" role="main" className="min-h-screen border-x hairline">{children}</main>
        <AgentDock />
      </div>
      <VoiceOrb onActivate={() => setCmdOpen(true)} />
      {cmdOpen && <CommandBar onClose={() => setCmdOpen(false)} />}
      <CopilotDrawer />
      <StatusBar />
      <SignOutModal
        open={signOutModalOpen}
        onClose={() => setSignOutModalOpen(false)}
        onConfirm={handleSignOutConfirm}
      />
      <SignOutAnimation active={signOutAnimating} onDone={handleSignOutAnimationDone} />
    </div>
  );
}

function Sidebar({ pathname, onSignOut }: { pathname: string; onSignOut: () => void }) {
  return (
    <aside className="sticky top-0 h-screen px-6 py-7 flex flex-col">
      <Link to="/" className="block group">
        <div className="flex items-baseline gap-2">
          <span className="font-display text-2xl tracking-tight">apa</span>
          <span className="font-display text-2xl text-accent">·</span>
          <span className="font-display text-2xl tracking-tight">os</span>
        </div>
        <p className="mt-1 text-[10px] uppercase tracking-[0.22em] text-muted-foreground">
          v3 · calm intelligence
        </p>
      </Link>

      <nav className="mt-8 flex-1 overflow-y-auto pr-1 -mr-1">
        <ul className="space-y-px">
          {NAV.map(item => {
            const active = pathname === item.to;
            return (
              <li key={item.to}>
                <Link
                  to={item.to}
                  className={[
                    "group flex items-baseline justify-between rounded-md px-3 py-1.5 transition-colors",
                    active
                      ? "bg-surface text-foreground"
                      : "text-muted-foreground hover:text-foreground hover:bg-surface/60",
                  ].join(" ")}
                >
                  <span className="text-[12.5px] tracking-tight">{item.label}</span>
                  <span className="text-[9px] uppercase tracking-[0.18em] opacity-60">
                    {item.hint}
                  </span>
                </Link>
              </li>
            );
          })}
        </ul>
      </nav>

      <div className="mt-4 border-t hairline pt-3 space-y-3">
        <AutonomyControl />

        <SignOutButton onClick={onSignOut} />

        <div className="flex items-center gap-2 text-[10px] text-muted-foreground">
          <span className="h-1.5 w-1.5 rounded-full bg-accent apa-pulse" />
          10 agents · 5 devices · memory live
        </div>
        <p className="text-[10px] text-muted-foreground/70">
          ⌘K command · double-space voice
        </p>
      </div>
    </aside>
  );
}

function AutonomyControl() {
  const autonomy = useApa(s => s.autonomy);
  const modes: { id: AutonomyMode; label: string }[] = [
    { id: "manual",     label: "Manual" },
    { id: "assist",     label: "Assist" },
    { id: "autonomous", label: "Auto" },
  ];
  return (
    <div>
      <p className="text-[9px] uppercase tracking-[0.18em] text-muted-foreground mb-1.5">Autonomy</p>
      <div className="grid grid-cols-3 gap-px rounded-md overflow-hidden border hairline bg-[var(--color-border)]">
        {modes.map(m => (
          <button
            key={m.id}
            onClick={() => apaStore.set(s => ({ ...s, autonomy: m.id }))}
            className={[
              "px-2 py-1 text-[10px] tracking-wide transition",
              autonomy === m.id
                ? "bg-accent text-accent-foreground"
                : "bg-background text-muted-foreground hover:text-foreground",
            ].join(" ")}
          >{m.label}</button>
        ))}
      </div>
    </div>
  );
}

/* ───────── Right Agent Dock ───────── */

function AgentDock() {
  const outcomes = useApa(s => s.outcomes);
  const focused = outcomes[0];
  const liveAgents: { id: AgentId; status: AgentStatus; conf?: number }[] = useMemo(() => {
    const all = Object.keys(AGENTS) as AgentId[];
    if (!focused) return all.map(id => ({ id, status: "idle" as AgentStatus }));
    const map = new Map(focused.agents.map(a => [a.agentId, a]));
    return all.map(id => ({
      id,
      status: map.get(id)?.status ?? "idle",
      conf: map.get(id)?.confidence,
    }));
  }, [focused]);

  return (
    <aside className="sticky top-0 h-screen px-5 py-7 overflow-y-auto">
      <p className="text-[9px] uppercase tracking-[0.22em] text-accent">Agent floor</p>
      <p className="mt-1 text-[11px] text-muted-foreground">
        {focused ? "Live · synced to current outcome" : "All idle · awaiting outcome"}
      </p>

      <ul className="mt-5 space-y-2">
        {liveAgents.map(a => (
          <li key={a.id} className="flex items-center justify-between gap-2 text-[11.5px]">
            <span className="flex items-center gap-2 min-w-0">
              <StatusDot status={a.status} />
              <span className="truncate">{AGENTS[a.id].name.replace(" Agent", "")}</span>
            </span>
            <span className="font-mono text-[9px] text-muted-foreground uppercase tracking-wider">
              {a.status}
            </span>
          </li>
        ))}
      </ul>

      <div className="mt-7 border-t hairline pt-5">
        <p className="text-[9px] uppercase tracking-[0.22em] text-muted-foreground">Current focus</p>
        {focused ? (
          <>
            <p className="mt-2 font-display text-[15px] leading-snug">{focused.text}</p>
            <p className="mt-2 text-[10px] text-muted-foreground">
              {focused.category} · {focused.priority} · {focused.currentStage}
            </p>
            <div className="mt-3 h-[2px] bg-[var(--color-border)] rounded">
              <div
                className="h-full bg-accent transition-all"
                style={{ width: `${stagePercent(focused.currentStage)}%` }}
              />
            </div>
          </>
        ) : (
          <p className="mt-2 text-[11px] text-muted-foreground italic">
            Say an outcome. Press ⌘K or double-tap space.
          </p>
        )}
      </div>

      <div className="mt-7 border-t hairline pt-5">
        <p className="text-[9px] uppercase tracking-[0.22em] text-muted-foreground">Devices</p>
        <DeviceMini />
      </div>
    </aside>
  );
}

function stagePercent(s: string) {
  const order = ["intent","agents","memory","world","predictions","plan","execution","complete"];
  return ((order.indexOf(s) + 1) / order.length) * 100;
}

function DeviceMini() {
  const devices = useApa(s => s.devices);
  return (
    <ul className="mt-2 space-y-1.5">
      {devices.slice(0, 5).map(d => (
        <li key={d.id} className="flex items-center justify-between text-[11px]">
          <span className="truncate">{d.name}</span>
          <span
            className="font-mono text-[9px] tracking-wider"
            style={{
              color: d.status === "connected" || d.status === "controlling" ? "var(--color-success)"
                   : d.status === "observed"  ? "var(--color-accent)"
                   : "var(--color-muted-foreground)",
            }}
          >{d.status}</span>
        </li>
      ))}
    </ul>
  );
}

function StatusDot({ status }: { status: AgentStatus }) {
  const cls =
    status === "running"  ? "bg-accent apa-pulse" :
    status === "thinking" ? "bg-accent/70 apa-pulse" :
    status === "queued"   ? "bg-muted-foreground/40" :
    status === "waiting"  ? "bg-warn" :
    status === "blocked"  ? "bg-destructive" :
    status === "failed"   ? "bg-destructive" :
    status === "done"     ? "bg-success" :
                            "bg-muted-foreground/25";
  return <span className={`h-1.5 w-1.5 rounded-full shrink-0 ${cls}`} />;
}

/* ───────── Voice Orb ───────── */

function VoiceOrb({ onActivate }: { onActivate: () => void }) {
  const outcomes = useApa(s => s.outcomes);
  const stage = outcomes[0]?.currentStage;
  const state =
    !stage              ? "idle"      :
    stage === "complete"? "success"   :
    stage === "execution"? "executing":
    stage === "plan"    ? "planning"  :
    stage === "agents"  ? "thinking"  :
                          "listening";

  const ring =
    state === "executing" ? "border-accent shadow-[0_0_48px_-8px_var(--color-accent)]"
    : state === "success" ? "border-[color:var(--color-success)] shadow-[0_0_48px_-12px_var(--color-success)]"
    : state === "thinking"? "border-accent/70"
    : state === "planning"? "border-accent"
    : state === "listening"? "border-accent apa-pulse"
    : "border-[color:var(--color-border-strong)]";

  return (
    <button
      onClick={onActivate}
      title="⌘K · double-space"
      className="fixed bottom-7 left-1/2 -translate-x-1/2 z-40 flex flex-col items-center gap-2 group"
    >
      <span className={`relative h-14 w-14 rounded-full border-2 ${ring} bg-background/80 backdrop-blur flex items-center justify-center transition`}>
        <span className="h-2 w-2 rounded-full bg-accent apa-pulse" />
        {state === "executing" && (
          <span className="absolute inset-0 rounded-full border-2 border-accent/40 animate-[spin_2.4s_linear_infinite] border-t-transparent" />
        )}
      </span>
      <span className="text-[9px] uppercase tracking-[0.22em] text-muted-foreground opacity-0 group-hover:opacity-100 transition">
        {state}
      </span>
    </button>
  );
}

/* ───────── Command Bar (⌘K) ───────── */

const QUICK = [
  "Help me prepare for tomorrow",
  "Open Instagram",
  "Send the attendance screenshot to Deepak",
  "Help me pass this semester",
  "Find my ATM Protocol notes",
  "Plan my next week",
  "What am I forgetting?",
];

function CommandBar({ onClose }: { onClose: () => void }) {
  const router = useRouter();
  const [q, setQ] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);
  useEffect(() => { inputRef.current?.focus(); }, []);

  const memory = useApa(s => s.memory);
  const goals = useApa(s => s.goals);
  const devices = useApa(s => s.devices);
  const notifications = useEnt(s => s.notifications);
  const activity = useEnt(s => s.activity);
  const pinned = useEnt(s => s.prefs.pinnedActions);

  const ql = q.toLowerCase();
  const navHits = NAV.filter(n => !ql || n.label.toLowerCase().includes(ql) || n.hint.toLowerCase().includes(ql)).slice(0, 6);
  const memHits = memory.filter(m => ql && m.text.toLowerCase().includes(ql)).slice(0, 3);
  const goalHits = goals.filter(g => ql && g.title.toLowerCase().includes(ql)).slice(0, 3);
  const devHits = devices.filter(d => ql && d.name.toLowerCase().includes(ql)).slice(0, 3);
  const notifHits = notifications.filter(n => ql && (n.title.toLowerCase().includes(ql) || n.body?.toLowerCase().includes(ql))).slice(0, 3);
  const actHits = activity.filter(a => ql && a.title.toLowerCase().includes(ql)).slice(0, 3);

  async function runIt(text: string) {
    pushActivity({ kind: "command", title: `Outcome · ${text}` });
    onClose();
    await router.navigate({ to: "/" });
    void runOutcome(text);
  }

  return (
    <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-start justify-center pt-[14vh]" onClick={onClose}>
      <div
        className="w-[min(640px,92vw)] rounded-xl border hairline-strong bg-background/95 shadow-2xl overflow-hidden"
        onClick={e => e.stopPropagation()}
      >
        <div className="flex items-center gap-3 px-5 py-4 border-b hairline">
          <span className="h-2 w-2 rounded-full bg-accent apa-pulse" />
          <input
            ref={inputRef}
            value={q}
            onChange={e => setQ(e.target.value)}
            onKeyDown={e => { if (e.key === "Enter" && q.trim()) runIt(q.trim()); }}
            placeholder="Outcomes · pages · devices · files · workflows · settings · people…"
            className="w-full bg-transparent outline-none text-[15px] placeholder:text-muted-foreground/50"
          />
          <kbd className="font-mono text-[10px] text-muted-foreground border hairline rounded px-1.5 py-0.5">ESC</kbd>
        </div>

        <div className="max-h-[60vh] overflow-y-auto py-2">
          {!q && (
            <>
              {pinned.length > 0 && (
                <Group label="Pinned">
                  {pinned.map(s => <Row key={s} onClick={() => runIt(s)} label={s} kind="pinned" />)}
                </Group>
              )}
              <Group label="Suggestions">
                {QUICK.map(s => (
                  <Row key={s} onClick={() => runIt(s)} label={s} kind="Outcome" />
                ))}
              </Group>
              <Group label="Recent activity">
                {activity.slice(0, 5).map(a => <Row key={a.id} label={a.title} kind={a.kind} />)}
              </Group>
            </>
          )}
          {q && (
            <>
              <Group label="Run as outcome">
                <Row onClick={() => runIt(q)} label={q} kind="↵ orchestrate" highlight />
              </Group>
              {navHits.length > 0 && (
                <Group label="Navigate">
                  {navHits.map(n => (
                    <Row key={n.to} onClick={() => { onClose(); router.navigate({ to: n.to }); }}
                         label={n.label} kind={n.hint} />
                  ))}
                </Group>
              )}
              {memHits.length > 0 && (
                <Group label="Memory">
                  {memHits.map(m => <Row key={m.id} label={m.text} kind={m.kind} />)}
                </Group>
              )}
              {goalHits.length > 0 && (
                <Group label="Goals">
                  {goalHits.map(g => <Row key={g.id} label={g.title} kind={`${g.progress}%`} onClick={() => { onClose(); router.navigate({ to: "/goals" }); }} />)}
                </Group>
              )}
              {devHits.length > 0 && (
                <Group label="Devices">
                  {devHits.map(d => <Row key={d.id} label={d.name} kind={d.status} onClick={() => { onClose(); router.navigate({ to: "/devices" }); }} />)}
                </Group>
              )}
              {notifHits.length > 0 && (
                <Group label="Notifications">
                  {notifHits.map(n => <Row key={n.id} label={n.title} kind={n.category} onClick={() => { onClose(); router.navigate({ to: "/notifications" }); }} />)}
                </Group>
              )}
              {actHits.length > 0 && (
                <Group label="Activity">
                  {actHits.map(a => <Row key={a.id} label={a.title} kind={a.kind} onClick={() => { onClose(); router.navigate({ to: "/timeline" }); }} />)}
                </Group>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}

function Group({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="px-2 py-1">
      <p className="px-3 pt-2 pb-1 text-[9px] uppercase tracking-[0.22em] text-muted-foreground">{label}</p>
      <ul>{children}</ul>
    </div>
  );
}
function Row({ label, kind, onClick, highlight }: { label: string; kind?: string; onClick?: () => void; highlight?: boolean }) {
  return (
    <li>
      <button
        onClick={onClick}
        className={[
          "w-full text-left flex items-center justify-between gap-4 px-3 py-2 rounded-md transition",
          highlight ? "bg-surface/60 text-foreground" : "hover:bg-surface/60 text-foreground/90",
        ].join(" ")}
      >
        <span className="truncate text-[13px]">{label}</span>
        {kind && <span className="font-mono text-[9px] uppercase tracking-wider text-muted-foreground shrink-0">{kind}</span>}
      </button>
    </li>
  );
}

/* ───────── Reusable headers / sections ───────── */

export function PageHeader({
  eyebrow, title, lede,
}: { eyebrow: string; title: string; lede?: string }) {
  return (
    <header className="border-b hairline px-10 pt-12 pb-9">
      <p className="text-[11px] uppercase tracking-[0.28em] text-accent">{eyebrow}</p>
      <h1 className="mt-4 font-display text-[44px] tracking-tight leading-[1.02]">{title}</h1>
      {lede && (
        <p className="mt-4 max-w-2xl text-[14px] leading-relaxed text-muted-foreground">{lede}</p>
      )}
    </header>
  );
}

export function Section({
  title, children, aside,
}: { title?: string; children: ReactNode; aside?: ReactNode }) {
  return (
    <section className="px-10 py-9 border-b hairline">
      {title && (
        <div className="mb-6 flex items-end justify-between gap-6">
          <h2 className="font-display text-2xl tracking-tight">{title}</h2>
          {aside}
        </div>
      )}
      {children}
    </section>
  );
}
