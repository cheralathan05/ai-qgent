import { createFileRoute, Link } from "@tanstack/react-router";
import { useState, useEffect } from "react";
import { Shell, PageHeader, Section } from "@/components/apa/Shell";
import { useApa } from "@/lib/apa/store";
import { useEnt } from "@/lib/apa/enterprise";
import { ApaOrb } from "@/components/apa/ApaOrb";

export const Route = createFileRoute("/dashboard")({
  head: () => ({ meta: [{ title: "Dashboard — APA-OS" }] }),
  component: DashboardPage,
});

function DashboardPage() {
  const devices = useApa((s) => s.devices);
  const outcomes = useApa((s) => s.outcomes);
  const goals = useApa((s) => s.goals);
  const memory = useApa((s) => s.memory);
  const notifications = useEnt((s) => s.notifications);
  const activity = useEnt((s) => s.activity);
  const [mounted, setMounted] = useState(false);

  useEffect(() => { setMounted(true); }, []);

  const online = devices.filter((d) => d.status === "connected" || d.status === "controlling").length;
  const success = outcomes.length
    ? Math.round((outcomes.filter((o) => o.currentStage === "complete").length / outcomes.length) * 100)
    : 0;
  const unreadNotifs = notifications.filter((n) => !n.read).length;

  return (
    <Shell>
      <section className="px-10 pt-12 pb-8 border-b hairline">
        <div className={`transition-all duration-700 ${mounted ? "opacity-100 translate-y-0" : "opacity-0 translate-y-4"}`}>
          <div className="flex items-center justify-between mb-6">
            <div>
              <p className="text-[10px] uppercase tracking-[0.28em] text-accent mb-2">Dashboard</p>
              <h1 className="font-display text-[36px] tracking-tight leading-[1.02]">
                System Overview
              </h1>
              <p className="mt-2 text-[13px] text-muted-foreground max-w-[440px]">
                Devices, agents, memory — one calm surface. Nothing flashing for the sake of it.
              </p>
            </div>
            <div className="hidden lg:block">
              <ApaOrb size={50} state="idle" />
            </div>
          </div>

          {/* Stats row */}
          <div className="grid grid-cols-2 lg:grid-cols-5 gap-3 stagger-children">
            {[
              { label: "Devices Online", value: `${online}/${devices.length}`, accent: true },
              { label: "Workflows", value: String(outcomes.length) },
              { label: "Success Rate", value: outcomes.length > 0 ? `${success}%` : "—" },
              { label: "Active Goals", value: String(goals.length) },
              { label: "Notifications", value: String(unreadNotifs), accent: unreadNotifs > 0 },
            ].map((stat, i) => (
              <div
                key={stat.label}
                className={`glass rounded-xl px-4 py-4 hover-lift card-expand`}
                style={{ animationDelay: `${i * 0.05}s` }}
              >
                <p className="text-[9px] uppercase tracking-[0.22em] text-muted-foreground">{stat.label}</p>
                <p className={`mt-2 font-display text-[22px] leading-none ${stat.accent ? "text-accent" : ""}`}>
                  {stat.value}
                </p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Quick actions */}
      <section className="px-10 py-8 border-b hairline">
        <p className="text-[9px] uppercase tracking-[0.22em] text-muted-foreground mb-4">Quick Actions</p>
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
          {[
            { to: "/", label: "New Outcome", detail: "State what you want", icon: "◎" },
            { to: "/pair-device", label: "Pair Device", detail: "Connect a new phone", icon: "⬡" },
            { to: "/knowledge", label: "Knowledge", detail: "Search your files", icon: "◈" },
            { to: "/assistant", label: "Voice Command", detail: "Push to talk", icon: "○" },
          ].map((action, i) => (
            <Link
              key={action.to + action.label}
              to={action.to}
              className="glass rounded-xl px-4 py-4 hover-lift hover-glow transition-all duration-300 group card-expand"
              style={{ animationDelay: `${i * 0.05}s` }}
            >
              <span className="text-accent text-[16px] group-hover:scale-110 inline-block transition-transform">{action.icon}</span>
              <p className="mt-2 text-[12px] font-medium">{action.label}</p>
              <p className="text-[10px] text-muted-foreground">{action.detail}</p>
            </Link>
          ))}
        </div>
      </section>

      {/* Content grid */}
      <div className="grid lg:grid-cols-[1fr_1fr] gap-0">
        {/* Recent workflows */}
        <section className="px-10 py-8 border-b lg:border-r hairline">
          <div className="flex items-end justify-between mb-4">
            <p className="text-[9px] uppercase tracking-[0.22em] text-accent">Recent Workflows</p>
            <Link to="/workflows" className="text-[10px] text-muted-foreground hover:text-foreground transition-colors">View all →</Link>
          </div>
          {outcomes.length === 0 ? (
            <div className="glass-subtle rounded-xl p-6 text-center">
              <p className="text-[12px] text-muted-foreground italic">No workflows yet.</p>
              <Link to="/" className="mt-2 inline-block text-[11px] text-accent hover:text-accent/80 transition-colors">
                Start your first outcome →
              </Link>
            </div>
          ) : (
            <ul className="space-y-2">
              {outcomes.slice(0, 5).map((o) => (
                <li key={o.id} className="glass-subtle rounded-xl px-4 py-3 hover-lift transition-all">
                  <div className="flex items-center justify-between">
                    <Link to="/" className="text-[12px] hover:text-accent line-clamp-1 flex-1">{o.text}</Link>
                    <span className="ml-3 text-[9px] font-mono uppercase tracking-wider text-accent shrink-0">{o.currentStage}</span>
                  </div>
                  <div className="mt-1 flex items-center gap-2">
                    <span className="text-[9px] uppercase tracking-wider text-muted-foreground">{o.category}</span>
                    <span className="text-muted-foreground/30">·</span>
                    <span className="text-[9px] uppercase tracking-wider text-muted-foreground">{o.priority}</span>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </section>

        {/* Connected devices */}
        <section className="px-10 py-8 border-b hairline">
          <div className="flex items-end justify-between mb-4">
            <p className="text-[9px] uppercase tracking-[0.22em] text-accent">Connected Devices</p>
            <Link to="/devices" className="text-[10px] text-muted-foreground hover:text-foreground transition-colors">View all →</Link>
          </div>
          <ul className="space-y-2">
            {devices.map((d) => (
              <li key={d.id} className="glass-subtle rounded-xl px-4 py-3 hover-lift transition-all">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className="w-8 h-8 rounded-lg bg-surface border hairline flex items-center justify-center">
                      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.2">
                        <rect x="5" y="2" width="14" height="20" rx="3" />
                        <line x1="12" y1="18" x2="12" y2="18.01" strokeWidth="2" strokeLinecap="round" />
                      </svg>
                    </div>
                    <div>
                      <p className="text-[12px] font-medium">{d.name}</p>
                      <p className="text-[9px] uppercase tracking-wider text-muted-foreground">{d.kind}</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-3">
                    {d.battery !== undefined && (
                      <span className="text-[10px] font-mono text-muted-foreground">{d.battery}%</span>
                    )}
                    <span
                      className="h-2 w-2 rounded-full"
                      style={{
                        backgroundColor:
                          d.status === "connected" || d.status === "controlling"
                            ? "var(--color-success)"
                            : d.status === "observed"
                            ? "var(--color-accent)"
                            : "var(--color-muted-foreground)",
                      }}
                    />
                  </div>
                </div>
              </li>
            ))}
          </ul>
        </section>
      </div>

      {/* Bottom row */}
      <div className="grid lg:grid-cols-[1fr_1fr] gap-0">
        {/* Activity */}
        <section className="px-10 py-8 border-b lg:border-r hairline">
          <p className="text-[9px] uppercase tracking-[0.22em] text-accent mb-4">Recent Activity</p>
          <div className="space-y-2">
            {activity.slice(0, 6).map((a) => (
              <div key={a.id} className="flex items-center gap-3 px-3 py-2 rounded-lg bg-surface/30">
                <span className="h-1.5 w-1.5 rounded-full bg-accent/50 shrink-0" />
                <span className="flex-1 text-[11px] text-muted-foreground truncate">{a.title}</span>
                <span className="text-[9px] font-mono text-muted-foreground/60 shrink-0">{a.kind}</span>
              </div>
            ))}
          </div>
        </section>

        {/* Memory */}
        <section className="px-10 py-8 border-b hairline">
          <div className="flex items-end justify-between mb-4">
            <p className="text-[9px] uppercase tracking-[0.22em] text-accent">Memory</p>
            <Link to="/memory" className="text-[10px] text-muted-foreground hover:text-foreground transition-colors">View all →</Link>
          </div>
          <div className="space-y-2">
            {memory.slice(0, 5).map((m) => (
              <div key={m.id} className="glass-subtle rounded-xl px-4 py-3">
                <div className="flex items-center justify-between mb-1">
                  <span className="text-[9px] uppercase tracking-[0.18em] text-accent">{m.kind}</span>
                  {m.confidence && (
                    <span className="text-[9px] font-mono text-muted-foreground">{m.confidence}%</span>
                  )}
                </div>
                <p className="text-[11.5px] text-muted-foreground leading-snug">{m.text}</p>
              </div>
            ))}
          </div>
        </section>
      </div>

      {/* Goals */}
      <section className="px-10 py-8 border-b hairline">
        <div className="flex items-end justify-between mb-4">
          <p className="text-[9px] uppercase tracking-[0.22em] text-accent">Active Goals</p>
          <Link to="/goals" className="text-[10px] text-muted-foreground hover:text-foreground transition-colors">View all →</Link>
        </div>
        <div className="grid sm:grid-cols-2 gap-3">
          {goals.map((g) => (
            <div key={g.id} className="glass rounded-xl px-5 py-4 hover-lift transition-all">
              <p className="text-[13px] font-medium">{g.title}</p>
              <p className="mt-1 text-[10px] text-muted-foreground">{g.horizon}</p>
              <div className="mt-3 flex items-center gap-3">
                <div className="flex-1 h-1.5 bg-[var(--color-border)] rounded-full overflow-hidden">
                  <div className="h-full bg-accent rounded-full transition-all" style={{ width: `${g.progress}%` }} />
                </div>
                <span className="text-[10px] font-mono text-accent">{g.progress}%</span>
              </div>
              <div className="mt-2 flex flex-wrap gap-1">
                {g.pillars.slice(0, 3).map((p) => (
                  <span key={p} className="px-2 py-0.5 rounded-full bg-surface text-[8px] uppercase tracking-wider text-muted-foreground">
                    {p}
                  </span>
                ))}
              </div>
            </div>
          ))}
        </div>
      </section>
    </Shell>
  );
}
