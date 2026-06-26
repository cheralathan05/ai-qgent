import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { useState, useEffect } from "react";
import { ApaOrb } from "@/components/apa/ApaOrb";
import { ParticleField } from "@/components/apa/ParticleField";
import { loginUser } from "@/lib/apa/enterprise";

export const Route = createFileRoute("/login")({
  head: () => ({ meta: [{ title: "Sign in — APA-OS" }] }),
  component: LoginPage,
});

const BENEFITS = [
  { icon: "◎", label: "10 AI agents", detail: "Working in parallel" },
  { icon: "⬡", label: "5 device types", detail: "Phone, laptop, browser, drive, cloud" },
  { icon: "◈", label: "Memory engine", detail: "Learns and recalls automatically" },
  { icon: "⟐", label: "Outcome-based", detail: "State goals, not steps" },
];

function LoginPage() {
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [pw, setPw] = useState("");
  const [showPw, setShowPw] = useState(false);
  const [remember, setRemember] = useState(true);
  const [loading, setLoading] = useState(false);
  const [mounted, setMounted] = useState(false);
  const [focusedField, setFocusedField] = useState<string | null>(null);

  useEffect(() => { setMounted(true); }, []);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!email || !pw) return;
    setLoading(true);
    await new Promise((r) => setTimeout(r, 1200));
    loginUser(email.split("@")[0], email);
    setLoading(false);
    navigate({ to: "/pair-device" });
  }

  return (
    <div className="min-h-screen bg-background text-foreground overflow-hidden">
      <div className="flex min-h-screen">
        {/* ─── Left Panel: Orb + Benefits ─── */}
        <div className="hidden lg:flex lg:w-[55%] relative items-center justify-center gradient-mesh">
          <ParticleField count={35} speed={0.15} opacity={0.25} />

          {/* Radial glow */}
          <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
            <div className="w-[600px] h-[600px] rounded-full" style={{
              background: "radial-gradient(circle, oklch(0.78 0.11 70 / 0.06) 0%, transparent 70%)",
            }} />
          </div>

          <div className={`relative z-10 flex flex-col items-center gap-10 transition-all duration-1000 ${mounted ? "opacity-100 translate-y-0" : "opacity-0 translate-y-8"}`}>
            <ApaOrb size={90} state="idle" />

            <div className="text-center">
              <h2 className="font-display text-[32px] tracking-tight">
                Calm intelligence,<br />unlimited reach.
              </h2>
              <p className="mt-3 text-[13px] text-muted-foreground max-w-[340px] leading-relaxed">
                One operating system that connects your devices, memory, and AI agents into a single, quiet surface.
              </p>
            </div>

            {/* Live benefits */}
            <div className="grid grid-cols-2 gap-3 w-full max-w-[420px]">
              {BENEFITS.map((b, i) => (
                <div
                  key={b.label}
                  className={`glass rounded-xl p-4 transition-all duration-500 ${mounted ? "opacity-100 translate-y-0" : "opacity-0 translate-y-4"}`}
                  style={{ transitionDelay: `${300 + i * 100}ms` }}
                >
                  <div className="flex items-center gap-2">
                    <span className="text-accent text-[14px]">{b.icon}</span>
                    <span className="text-[12px] font-medium">{b.label}</span>
                  </div>
                  <p className="mt-1 text-[10.5px] text-muted-foreground">{b.detail}</p>
                </div>
              ))}
            </div>

            {/* Live status */}
            <div className={`flex items-center gap-3 text-[10px] text-muted-foreground transition-all duration-500 ${mounted ? "opacity-100" : "opacity-0"}`} style={{ transitionDelay: "800ms" }}>
              <span className="flex items-center gap-1.5">
                <span className="h-1.5 w-1.5 rounded-full bg-[color:var(--color-success)] apa-pulse" />
                10 agents ready
              </span>
              <span>·</span>
              <span>5 devices connected</span>
              <span>·</span>
              <span>memory active</span>
            </div>
          </div>
        </div>

        {/* ─── Right Panel: Login Form ─── */}
        <div className="flex-1 flex items-center justify-center px-6 py-12 lg:px-12">
          <div className={`w-full max-w-[400px] transition-all duration-700 ${mounted ? "opacity-100 translate-y-0" : "opacity-0 translate-y-6"}`} style={{ transitionDelay: "200ms" }}>
            {/* Mobile logo */}
            <div className="lg:hidden flex flex-col items-center mb-10">
              <ApaOrb size={60} state="idle" />
              <h1 className="mt-4 font-display text-[28px] tracking-tight">
                APA<span className="text-accent">-</span>OS
              </h1>
            </div>

            <div className="hidden lg:block">
              <Link to="/" className="inline-flex items-center gap-2 mb-10">
                <span className="font-display text-[22px] tracking-tight">apa<span className="text-accent">·</span>os</span>
                <span className="text-[9px] uppercase tracking-[0.18em] text-muted-foreground/60 ml-2">v3</span>
              </Link>
            </div>

            <h1 className="font-display text-[28px] tracking-tight">Welcome back.</h1>
            <p className="mt-2 text-[13px] text-muted-foreground">Sign in to your operating system.</p>

            <form onSubmit={handleSubmit} className="mt-8 space-y-5">
              {/* Email */}
              <div className="relative">
                <label className="block">
                  <span className={`text-[9px] uppercase tracking-[0.22em] transition-colors duration-200 ${focusedField === "email" ? "text-accent" : "text-muted-foreground"}`}>
                    Email
                  </span>
                  <input
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    onFocus={() => setFocusedField("email")}
                    onBlur={() => setFocusedField(null)}
                    placeholder="you@example.com"
                    className="mt-2 w-full bg-transparent border hairline rounded-xl px-4 py-3 text-[14px] outline-none focus:border-accent input-glow transition-all duration-200 placeholder:text-muted-foreground/30"
                    autoComplete="email"
                  />
                </label>
              </div>

              {/* Password */}
              <div className="relative">
                <label className="block">
                  <span className={`text-[9px] uppercase tracking-[0.22em] transition-colors duration-200 ${focusedField === "password" ? "text-accent" : "text-muted-foreground"}`}>
                    Password
                  </span>
                  <div className="relative mt-2">
                    <input
                      type={showPw ? "text" : "password"}
                      value={pw}
                      onChange={(e) => setPw(e.target.value)}
                      onFocus={() => setFocusedField("password")}
                      onBlur={() => setFocusedField(null)}
                      placeholder="Enter your password"
                      className="w-full bg-transparent border hairline rounded-xl px-4 py-3 pr-12 text-[14px] outline-none focus:border-accent input-glow transition-all duration-200 placeholder:text-muted-foreground/30"
                      autoComplete="current-password"
                    />
                    <button
                      type="button"
                      onClick={() => setShowPw(!showPw)}
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground transition-colors p-1"
                      tabIndex={-1}
                    >
                      <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5">
                        {showPw ? (
                          <>
                            <path d="M1 8s2.5-5 7-5 7 5 7 5-2.5 5-7 5-7-5-7-5z" />
                            <circle cx="8" cy="8" r="2" />
                          </>
                        ) : (
                          <>
                            <path d="M1 8s2.5-5 7-5 7 5 7 5-2.5 5-7 5-7-5-7-5z" />
                            <line x1="2" y1="2" x2="14" y2="14" />
                          </>
                        )}
                      </svg>
                    </button>
                  </div>
                </label>
              </div>

              {/* Remember me + forgot */}
              <div className="flex items-center justify-between">
                <label className="flex items-center gap-2 cursor-pointer group">
                  <div
                    className={`w-4 h-4 rounded border transition-all duration-200 flex items-center justify-center ${
                      remember
                        ? "bg-accent border-accent"
                        : "border-muted-foreground/30 group-hover:border-muted-foreground/50"
                    }`}
                    onClick={() => setRemember(!remember)}
                  >
                    {remember && (
                      <svg width="10" height="8" viewBox="0 0 10 8" fill="none">
                        <path d="M1 4L3.5 6.5L9 1" stroke="oklch(0.14 0 0)" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
                      </svg>
                    )}
                  </div>
                  <span className="text-[11px] text-muted-foreground group-hover:text-foreground transition-colors">Remember me</span>
                </label>
                <Link to="/forgot-password" className="text-[11px] text-accent hover:text-accent/80 transition-colors">
                  Forgot password?
                </Link>
              </div>

              {/* Submit */}
              <button
                type="submit"
                disabled={!email || !pw || loading}
                className="w-full py-3.5 rounded-xl bg-accent text-accent-foreground text-[12px] uppercase tracking-[0.22em] font-medium transition-all duration-300 disabled:opacity-40 disabled:cursor-not-allowed hover:brightness-110 hover:shadow-[0_0_30px_-4px_oklch(0.78_0.11_70/0.4)] active:scale-[0.98]"
              >
                {loading ? (
                  <span className="flex items-center justify-center gap-2">
                    <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24" fill="none">
                      <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="2" opacity="0.3" />
                      <path d="M12 2a10 10 0 019.95 9" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
                    </svg>
                    Signing in…
                  </span>
                ) : (
                  "Sign in"
                )}
              </button>
            </form>

            {/* Divider */}
            <div className="my-7 flex items-center gap-3">
              <span className="flex-1 h-px bg-[var(--color-border)]" />
              <span className="text-[9px] uppercase tracking-[0.22em] text-muted-foreground/60">or continue with</span>
              <span className="flex-1 h-px bg-[var(--color-border)]" />
            </div>

            {/* Social providers */}
            <div className="grid grid-cols-3 gap-3">
              {[
                { name: "Google", icon: (
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
                    <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 01-2.2 3.32v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.1z" />
                    <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" />
                    <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" />
                    <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" />
                  </svg>
                )},
                { name: "GitHub", icon: (
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
                    <path d="M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205 11.385.6.105.825-.255.825-.57 0-.285-.015-1.23-.015-2.235-3.015.555-3.795-.735-4.035-1.41-.135-.345-.72-1.41-1.23-1.695-.42-.225-1.02-.78-.015-.795.945-.015 1.62.87 1.845 1.23 1.08 1.815 2.805 1.305 3.495.99.105-.78.42-1.305.765-1.605-2.67-.3-5.46-1.335-5.46-5.925 0-1.305.465-2.385 1.23-3.225-.12-.3-.54-1.53.12-3.18 0 0 1.005-.315 3.3 1.23.96-.27 1.98-.405 3-.405s2.04.135 3 .405c2.295-1.56 3.3-1.23 3.3-1.23.66 1.65.24 2.88.12 3.18.765.84 1.23 1.905 1.23 3.225 0 4.605-2.805 5.625-5.475 5.925.435.375.81 1.095.81 2.22 0 1.605-.015 2.895-.015 3.3 0 .315.225.69.825.57A12.02 12.02 0 0024 12c0-6.63-5.37-12-12-12z" />
                  </svg>
                )},
                { name: "Microsoft", icon: (
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
                    <path d="M11.4 24H0V12.6h11.4V24zM24 24H12.6V12.6H24V24zM11.4 11.4H0V0h11.4v11.4zm12.6 0H12.6V0H24v11.4z" />
                  </svg>
                )},
              ].map((p) => (
                <button
                  key={p.name}
                  type="button"
                  className="flex items-center justify-center gap-2 py-3 rounded-xl border hairline text-[11px] text-muted-foreground hover:text-foreground hover:border-accent/40 hover:bg-surface/40 transition-all duration-200"
                >
                  {p.icon}
                  <span className="hidden sm:inline">{p.name}</span>
                </button>
              ))}
            </div>

            {/* Security indicator */}
            <div className="mt-7 flex items-center justify-center gap-2 text-[9px] text-muted-foreground/50">
              <svg width="12" height="12" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.2">
                <rect x="3" y="7" width="10" height="7" rx="1.5" />
                <path d="M5 7V5a3 3 0 016 0v2" />
              </svg>
              <span>End-to-end encrypted · JWT secured</span>
            </div>

            {/* Register link */}
            <p className="mt-6 text-center text-[12px] text-muted-foreground">
              Don&apos;t have an account?{" "}
              <Link to="/register" className="text-accent hover:text-accent/80 transition-colors font-medium">
                Create one
              </Link>
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
