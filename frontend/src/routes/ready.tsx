import { createFileRoute, Link } from "@tanstack/react-router";
import { useState, useEffect } from "react";
import { ApaOrb } from "@/components/apa/ApaOrb";
import { ParticleField } from "@/components/apa/ParticleField";

export const Route = createFileRoute("/ready")({
  head: () => ({ meta: [{ title: "Ready — APA-OS" }] }),
  component: ReadyPage,
});

const SYSTEM_CARDS = [
  { id: "device", label: "Device Control", status: "ready", icon: "◎", detail: "Pixel 8 Pro connected" },
  { id: "phone", label: "Phone Intelligence", status: "ready", icon: "⬡", detail: "Screen · OCR · Navigation" },
  { id: "knowledge", label: "Knowledge Engine", status: "ready", icon: "◈", detail: "412 documents indexed" },
  { id: "memory", label: "Memory Engine", status: "ready", icon: "◇", detail: "5 memories active" },
  { id: "voice", label: "Voice Assistant", status: "ready", icon: "○", detail: "Push-to-talk enabled" },
  { id: "agent", label: "Agent Engine", status: "ready", icon: "⟐", detail: "10 agents deployed" },
];

const LIVE_EVENTS = [
  { time: "2m ago", label: "Device connected via USB", type: "device" },
  { time: "5m ago", label: "Memory engine indexed 3 new items", type: "memory" },
  { time: "8m ago", label: "Knowledge base synced", type: "knowledge" },
  { time: "12m ago", label: "Agent swarm initialized", type: "agent" },
];

function ReadyPage() {
  const [mounted, setMounted] = useState(false);
  const [entered, setEntered] = useState(false);

  useEffect(() => { setMounted(true); }, []);

  return (
    <div className="min-h-screen bg-background text-foreground overflow-hidden">
      {/* Background */}
      <div className="fixed inset-0 gradient-mesh" />
      <ParticleField count={30} speed={0.1} opacity={0.2} />

      {/* Content */}
      <div className="relative z-10 min-h-screen flex flex-col">
        {/* Header */}
        <header className="px-6 lg:px-10 py-6">
          <div className="max-w-[1400px] mx-auto flex items-center justify-between">
            <Link to="/" className="flex items-center gap-2">
              <ApaOrb size={24} state="idle" />
              <span className="font-display text-[18px] tracking-tight">apa<span className="text-accent">·</span>os</span>
            </Link>
            <span className="text-[10px] uppercase tracking-[0.18em] text-muted-foreground">
              Onboarding · Step 5 of 5
            </span>
          </div>
        </header>

        {/* Main */}
        <main className="flex-1 flex items-center justify-center px-6 py-8">
          <div className={`w-full max-w-[1000px] transition-all duration-1000 ${mounted ? "opacity-100 translate-y-0" : "opacity-0 translate-y-8"}`}>
            {/* Hero */}
            <div className="text-center mb-12">
              <div className="mx-auto mb-6">
                <ApaOrb size={90} state="success" />
              </div>
              <p className={`text-[10px] uppercase tracking-[0.35em] text-accent mb-4 transition-all duration-700 ${mounted ? "opacity-100" : "opacity-0"}`} style={{ transitionDelay: "200ms" }}>
                Welcome Back
              </p>
              <h1 className={`font-display text-[40px] lg:text-[52px] tracking-tight leading-[1.02] transition-all duration-700 ${mounted ? "opacity-100 translate-y-0" : "opacity-0 translate-y-4"}`} style={{ transitionDelay: "300ms" }}>
                Hello Cheralathan
              </h1>
              <p className={`mt-4 text-[15px] text-muted-foreground max-w-[460px] mx-auto leading-relaxed transition-all duration-700 ${mounted ? "opacity-100" : "opacity-0"}`} style={{ transitionDelay: "400ms" }}>
                Your AI Operating System is ready. Everything is connected, verified, and waiting for your first outcome.
              </p>
            </div>

            {/* Quick stats */}
            <div className={`grid grid-cols-2 lg:grid-cols-4 gap-3 mb-8 transition-all duration-500 ${mounted ? "opacity-100" : "opacity-0"}`} style={{ transitionDelay: "500ms" }}>
              {[
                { label: "Connected Device", value: "Pixel 8 Pro" },
                { label: "Battery", value: "78%" },
                { label: "Current App", value: "Chrome" },
                { label: "System Health", value: "Optimal" },
              ].map((s) => (
                <div key={s.label} className="glass rounded-xl px-4 py-3 text-center">
                  <p className="text-[9px] uppercase tracking-[0.18em] text-muted-foreground">{s.label}</p>
                  <p className="mt-1 text-[13px] font-medium">{s.value}</p>
                </div>
              ))}
            </div>

            {/* System Status Cards */}
            <div className={`grid sm:grid-cols-2 lg:grid-cols-3 gap-3 mb-8 transition-all duration-500 stagger-children ${mounted ? "opacity-100" : "opacity-0"}`} style={{ transitionDelay: "600ms" }}>
              {SYSTEM_CARDS.map((card) => (
                <div key={card.id} className="glass rounded-xl px-5 py-4 hover-lift card-expand">
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-2">
                      <span className="text-accent text-[14px]">{card.icon}</span>
                      <span className="text-[12px] font-medium">{card.label}</span>
                    </div>
                    <span className="flex items-center gap-1.5">
                      <span className="h-1.5 w-1.5 rounded-full bg-[color:var(--color-success)]" />
                      <span className="text-[9px] uppercase tracking-wider text-[color:var(--color-success)]">{card.status}</span>
                    </span>
                  </div>
                  <p className="text-[10.5px] text-muted-foreground">{card.detail}</p>
                </div>
              ))}
            </div>

            {/* Live Preview */}
            <div className={`glass rounded-2xl p-6 mb-8 transition-all duration-500 ${mounted ? "opacity-100" : "opacity-0"}`} style={{ transitionDelay: "700ms" }}>
              <div className="grid lg:grid-cols-[1fr_1fr] gap-6">
                {/* Recent Events */}
                <div>
                  <p className="text-[9px] uppercase tracking-[0.22em] text-accent mb-3">Recent Events</p>
                  <div className="space-y-2">
                    {LIVE_EVENTS.map((event, i) => (
                      <div key={i} className="flex items-center gap-3 px-3 py-2 rounded-lg bg-surface/30">
                        <span className="h-1.5 w-1.5 rounded-full bg-accent/50 shrink-0" />
                        <span className="flex-1 text-[11px] text-muted-foreground">{event.label}</span>
                        <span className="text-[9px] font-mono text-muted-foreground/60">{event.time}</span>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Knowledge & Memory Stats */}
                <div>
                  <p className="text-[9px] uppercase tracking-[0.22em] text-accent mb-3">System Overview</p>
                  <div className="space-y-3">
                    {[
                      { label: "Knowledge Sources", value: "4 synced", progress: 85 },
                      { label: "Memory Entries", value: "5 active", progress: 60 },
                      { label: "Agent Tasks", value: "0 in queue", progress: 0 },
                      { label: "Device Capabilities", value: "6 enabled", progress: 100 },
                    ].map((item) => (
                      <div key={item.label}>
                        <div className="flex items-center justify-between mb-1">
                          <span className="text-[11px]">{item.label}</span>
                          <span className="text-[10px] font-mono text-muted-foreground">{item.value}</span>
                        </div>
                        <div className="h-1 bg-[var(--color-border)] rounded-full overflow-hidden">
                          <div className="h-full bg-accent/60 rounded-full" style={{ width: `${item.progress}%` }} />
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </div>

            {/* Launch CTA */}
            <div className={`text-center transition-all duration-700 ${mounted ? "opacity-100 translate-y-0" : "opacity-0 translate-y-4"}`} style={{ transitionDelay: "800ms" }}>
              <Link
                to="/dashboard"
                className="group relative inline-flex items-center gap-3 px-12 py-5 rounded-2xl bg-accent text-accent-foreground text-[14px] uppercase tracking-[0.25em] font-medium transition-all duration-300 hover:brightness-110 hover:shadow-[0_0_60px_-8px_oklch(0.78_0.11_70/0.5)] active:scale-[0.97] btn-glow"
                onClick={() => setEntered(true)}
              >
                <ApaOrb size={20} state="idle" />
                <span>Launch APA-OS</span>
                <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" className="group-hover:translate-x-1 transition-transform">
                  <path d="M3 8h10M9 4l4 4-4 4" />
                </svg>
              </Link>
              <p className="mt-4 text-[10px] text-muted-foreground/50">
                Press Enter or click to enter your operating system
              </p>
            </div>
          </div>
        </main>
      </div>
    </div>
  );
}
