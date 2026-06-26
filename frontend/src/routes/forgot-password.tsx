import { createFileRoute, Link } from "@tanstack/react-router";
import { useState, useEffect } from "react";
import { ApaOrb } from "@/components/apa/ApaOrb";

export const Route = createFileRoute("/forgot-password")({
  head: () => ({ meta: [{ title: "Reset password — APA-OS" }] }),
  component: ForgotPage,
});

function ForgotPage() {
  const [email, setEmail] = useState("");
  const [sent, setSent] = useState(false);
  const [loading, setLoading] = useState(false);
  const [mounted, setMounted] = useState(false);
  const [focusedField, setFocusedField] = useState(false);

  useEffect(() => { setMounted(true); }, []);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!email) return;
    setLoading(true);
    await new Promise((r) => setTimeout(r, 1000));
    setLoading(false);
    setSent(true);
  }

  return (
    <div className="min-h-screen bg-background text-foreground grain flex items-center justify-center px-6 gradient-mesh">
      <div className={`w-full max-w-[420px] transition-all duration-700 ${mounted ? "opacity-100 translate-y-0" : "opacity-0 translate-y-6"}`}>
        {/* Logo */}
        <Link to="/" className="flex flex-col items-center mb-10">
          <ApaOrb size={50} state="idle" />
          <h1 className="mt-3 font-display text-[22px] tracking-tight">
            apa<span className="text-accent">·</span>os
          </h1>
        </Link>

        {sent ? (
          /* Success state */
          <div className="glass rounded-2xl p-8 text-center card-expand">
            <div className="mx-auto w-14 h-14 rounded-full bg-[color:var(--color-success)]/10 flex items-center justify-center mb-5">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
                <path d="M5 12l5 5L19 7" stroke="oklch(0.72 0.12 150)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="check-draw" style={{ strokeDasharray: 24 }} />
              </svg>
            </div>
            <h2 className="font-display text-[20px] tracking-tight">Check your email</h2>
            <p className="mt-2 text-[13px] text-muted-foreground leading-relaxed">
              We sent a password reset link to{" "}
              <span className="text-foreground font-medium">{email}</span>.
              <br />The link expires in 30 minutes.
            </p>
            <button
              onClick={() => { setSent(false); setEmail(""); }}
              className="mt-6 text-[11px] text-accent hover:text-accent/80 transition-colors uppercase tracking-[0.18em]"
            >
              Send again
            </button>
          </div>
        ) : (
          /* Form state */
          <>
            <h1 className="font-display text-[28px] tracking-tight text-center">Reset password.</h1>
            <p className="mt-2 text-[13px] text-muted-foreground text-center">We&apos;ll send you a magic link.</p>

            <form onSubmit={handleSubmit} className="mt-8 space-y-5">
              <div className="relative">
                <label className="block">
                  <span className={`text-[9px] uppercase tracking-[0.22em] transition-colors duration-200 ${focusedField ? "text-accent" : "text-muted-foreground"}`}>
                    Email address
                  </span>
                  <input
                    type="email"
                    required
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    onFocus={() => setFocusedField(true)}
                    onBlur={() => setFocusedField(false)}
                    placeholder="you@example.com"
                    className="mt-2 w-full bg-transparent border hairline rounded-xl px-4 py-3 text-[14px] outline-none focus:border-accent input-glow transition-all duration-200 placeholder:text-muted-foreground/30"
                    autoComplete="email"
                  />
                </label>
              </div>

              <button
                type="submit"
                disabled={!email || loading}
                className="w-full py-3.5 rounded-xl bg-accent text-accent-foreground text-[12px] uppercase tracking-[0.22em] font-medium transition-all duration-300 disabled:opacity-40 disabled:cursor-not-allowed hover:brightness-110 hover:shadow-[0_0_30px_-4px_oklch(0.78_0.11_70/0.4)] active:scale-[0.98]"
              >
                {loading ? (
                  <span className="flex items-center justify-center gap-2">
                    <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24" fill="none">
                      <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="2" opacity="0.3" />
                      <path d="M12 2a10 10 0 019.95 9" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
                    </svg>
                    Sending…
                  </span>
                ) : (
                  "Send reset link"
                )}
              </button>
            </form>
          </>
        )}

        <p className="mt-8 text-center text-[12px] text-muted-foreground">
          <Link to="/login" className="hover:text-foreground transition-colors">
            ← Back to sign in
          </Link>
        </p>
      </div>
    </div>
  );
}
