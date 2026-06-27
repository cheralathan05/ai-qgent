import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { useState, useEffect } from "react";
import { ApaOrb } from "@/components/apa/ApaOrb";
import { ParticleField } from "@/components/apa/ParticleField";
import { authApi } from "@/lib/api/auth";
import { AxiosError } from "axios";

export const Route = createFileRoute("/register")({
  head: () => ({ meta: [{ title: "Create account — APA-OS" }] }),
  component: RegisterPage,
});

function RegisterPage() {
  const navigate = useNavigate();
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [pw, setPw] = useState("");
  const [confirmPw, setConfirmPw] = useState("");
  const [showPw, setShowPw] = useState(false);
  const [loading, setLoading] = useState(false);
  const [mounted, setMounted] = useState(false);
  const [focusedField, setFocusedField] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  useEffect(() => { setMounted(true); }, []);

  const pwStrength = pw.length === 0 ? 0 : pw.length < 6 ? 1 : pw.length < 10 ? 2 : /[A-Z]/.test(pw) && /[0-9]/.test(pw) && /[^A-Za-z0-9]/.test(pw) ? 4 : 3;
  const pwMatch = confirmPw.length > 0 && pw === confirmPw;
  const pwMismatch = confirmPw.length > 0 && pw !== confirmPw;
  const canSubmit = name.length > 0 && email.length > 0 && pw.length >= 6 && pw === confirmPw;

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!canSubmit) return;
    setLoading(true);
    setError(null);
    try {
      const res = await authApi.register({
        full_name: name,
        email,
        password: pw,
      });
      if (res.success) {
        setSuccess(true);
      }
    } catch (err) {
      const axiosErr = err as AxiosError<{ detail: string }>;
      if (axiosErr.response?.data?.detail) {
        setError(axiosErr.response.data.detail);
      } else if (axiosErr.response?.status === 409) {
        setError("An account with this email already exists.");
      } else if (axiosErr.response?.status === 422) {
        setError("Invalid input. Please check your information.");
      } else {
        setError("Something went wrong. Please try again.");
      }
    } finally {
      setLoading(false);
    }
  }

  if (success) {
    return (
      <div className="min-h-screen bg-background text-foreground grain flex items-center justify-center px-6 gradient-mesh">
        <div className={`w-full max-w-[420px] transition-all duration-700 ${mounted ? "opacity-100 translate-y-0" : "opacity-0 translate-y-6"}`}>
          <Link to="/" className="flex flex-col items-center mb-10">
            <ApaOrb size={50} state="idle" />
            <h1 className="mt-3 font-display text-[22px] tracking-tight">
              apa<span className="text-accent">·</span>os
            </h1>
          </Link>

          <div className="glass rounded-2xl p-8 text-center card-expand">
            <div className="mx-auto w-14 h-14 rounded-full bg-[color:var(--color-success)]/10 flex items-center justify-center mb-5">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
                <path d="M5 12l5 5L19 7" stroke="oklch(0.72 0.12 150)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="check-draw" style={{ strokeDasharray: 24 }} />
              </svg>
            </div>
            <h2 className="font-display text-[20px] tracking-tight">Account created</h2>
            <p className="mt-2 text-[13px] text-muted-foreground leading-relaxed">
              Your account has been created successfully.<br />
              You can now sign in.
            </p>
            <Link
              to="/login"
              className="mt-6 inline-block text-[11px] text-accent hover:text-accent/80 transition-colors uppercase tracking-[0.18em]"
            >
              Continue to sign in
            </Link>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background text-foreground overflow-hidden">
      <div className="flex min-h-screen">
        <div className="hidden lg:flex lg:w-[55%] relative items-center justify-center gradient-mesh">
          <ParticleField count={35} speed={0.15} opacity={0.25} />
          <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
            <div className="w-[600px] h-[600px] rounded-full" style={{
              background: "radial-gradient(circle, oklch(0.78 0.11 70 / 0.06) 0%, transparent 70%)",
            }} />
          </div>

          <div className={`relative z-10 flex flex-col items-center gap-10 transition-all duration-1000 ${mounted ? "opacity-100 translate-y-0" : "opacity-0 translate-y-8"}`}>
            <ApaOrb size={90} state="idle" />
            <div className="text-center">
              <h2 className="font-display text-[32px] tracking-tight">
                Your intelligence,<br />your rules.
              </h2>
              <p className="mt-3 text-[13px] text-muted-foreground max-w-[340px] leading-relaxed">
                Create your APA-OS account. In five minutes, your AI operating system will be fully connected.
              </p>
            </div>

            <div className="flex flex-col gap-3 w-full max-w-[340px]">
              {[
                "Connect your phone via QR or USB",
                "Grant permissions you control",
                "Run your first outcome instantly",
              ].map((text, i) => (
                <div
                  key={text}
                  className={`flex items-center gap-3 glass rounded-xl px-4 py-3 transition-all duration-500 ${mounted ? "opacity-100 translate-y-0" : "opacity-0 translate-y-4"}`}
                  style={{ transitionDelay: `${400 + i * 100}ms` }}
                >
                  <span className="h-5 w-5 rounded-full bg-accent/10 flex items-center justify-center shrink-0">
                    <svg width="10" height="8" viewBox="0 0 10 8" fill="none">
                      <path d="M1 4L3.5 6.5L9 1" stroke="oklch(0.78 0.11 70)" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
                    </svg>
                  </span>
                  <span className="text-[12px] text-muted-foreground">{text}</span>
                </div>
              ))}
            </div>
          </div>
        </div>

        <div className="flex-1 flex items-center justify-center px-6 py-12 lg:px-12">
          <div className={`w-full max-w-[400px] transition-all duration-700 ${mounted ? "opacity-100 translate-y-0" : "opacity-0 translate-y-6"}`} style={{ transitionDelay: "200ms" }}>
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

            <h1 className="font-display text-[28px] tracking-tight">Begin.</h1>
            <p className="mt-2 text-[13px] text-muted-foreground">Your AI operating system starts here.</p>

            {error && (
              <div className="mt-4 p-3 rounded-xl bg-destructive/10 border border-destructive/30 text-[12px] text-destructive">
                {error}
              </div>
            )}

            <form onSubmit={handleSubmit} className="mt-8 space-y-5">
              <div className="relative">
                <label className="block">
                  <span className={`text-[9px] uppercase tracking-[0.22em] transition-colors duration-200 ${focusedField === "name" ? "text-accent" : "text-muted-foreground"}`}>
                    Full name
                  </span>
                  <input
                    type="text"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    onFocus={() => setFocusedField("name")}
                    onBlur={() => setFocusedField(null)}
                    placeholder="Cheralathan"
                    className="mt-2 w-full bg-transparent border hairline rounded-xl px-4 py-3 text-[14px] outline-none focus:border-accent input-glow transition-all duration-200 placeholder:text-muted-foreground/30"
                    autoComplete="name"
                  />
                </label>
              </div>

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
                      placeholder="Min 8 characters"
                      className="w-full bg-transparent border hairline rounded-xl px-4 py-3 pr-12 text-[14px] outline-none focus:border-accent input-glow transition-all duration-200 placeholder:text-muted-foreground/30"
                      autoComplete="new-password"
                    />
                    <button
                      type="button"
                      onClick={() => setShowPw(!showPw)}
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground transition-colors p-1"
                      tabIndex={-1}
                    >
                      <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5">
                        {showPw ? (
                          <><path d="M1 8s2.5-5 7-5 7 5 7 5-2.5 5-7 5-7-5-7-5z" /><circle cx="8" cy="8" r="2" /></>
                        ) : (
                          <><path d="M1 8s2.5-5 7-5 7 5 7 5-2.5 5-7 5-7-5-7-5z" /><line x1="2" y1="2" x2="14" y2="14" /></>
                        )}
                      </svg>
                    </button>
                  </div>
                </label>
                {pw.length > 0 && (
                  <div className="mt-2 flex items-center gap-2">
                    <div className="flex-1 flex gap-1">
                      {[1, 2, 3, 4].map((i) => (
                        <div
                          key={i}
                          className={`h-1 flex-1 rounded-full transition-all duration-300 ${i <= pwStrength ? strengthColors[pwStrength] : "bg-muted-foreground/15"}`}
                        />
                      ))}
                    </div>
                    <span className="text-[9px] uppercase tracking-wider text-muted-foreground/60">{strengthLabels[pwStrength]}</span>
                  </div>
                )}
              </div>

              <div className="relative">
                <label className="block">
                  <span className={`text-[9px] uppercase tracking-[0.22em] transition-colors duration-200 ${focusedField === "confirm" ? "text-accent" : "text-muted-foreground"}`}>
                    Confirm password
                  </span>
                  <input
                    type={showPw ? "text" : "password"}
                    value={confirmPw}
                    onChange={(e) => setConfirmPw(e.target.value)}
                    onFocus={() => setFocusedField("confirm")}
                    onBlur={() => setFocusedField(null)}
                    placeholder="Re-enter password"
                    className={`mt-2 w-full bg-transparent border rounded-xl px-4 py-3 text-[14px] outline-none input-glow transition-all duration-200 placeholder:text-muted-foreground/30 ${
                      pwMatch ? "border-[color:var(--color-success)]" : pwMismatch ? "border-destructive" : "hairline focus:border-accent"
                    }`}
                    autoComplete="new-password"
                  />
                </label>
                {pwMatch && (
                  <span className="absolute right-3 top-[38px] text-[color:var(--color-success)]">
                    <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
                      <path d="M3 7L6 10L11 4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
                    </svg>
                  </span>
                )}
              </div>

              <button
                type="submit"
                disabled={!canSubmit || loading}
                className="w-full py-3.5 rounded-xl bg-accent text-accent-foreground text-[12px] uppercase tracking-[0.22em] font-medium transition-all duration-300 disabled:opacity-40 disabled:cursor-not-allowed hover:brightness-110 hover:shadow-[0_0_30px_-4px_oklch(0.78_0.11_70/0.4)] active:scale-[0.98]"
              >
                {loading ? (
                  <span className="flex items-center justify-center gap-2">
                    <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24" fill="none">
                      <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="2" opacity="0.3" />
                      <path d="M12 2a10 10 0 019.95 9" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
                    </svg>
                    Creating account…
                  </span>
                ) : (
                  "Create account"
                )}
              </button>
            </form>

            <p className="mt-5 text-center text-[10px] text-muted-foreground/50 leading-relaxed">
              By creating an account, you agree to our{" "}
              <span className="text-muted-foreground/70 cursor-pointer hover:text-foreground transition-colors">Terms</span>
              {" "}and{" "}
              <span className="text-muted-foreground/70 cursor-pointer hover:text-foreground transition-colors">Privacy Policy</span>.
            </p>

            <p className="mt-6 text-center text-[12px] text-muted-foreground">
              Already have an account?{" "}
              <Link to="/login" className="text-accent hover:text-accent/80 transition-colors font-medium">
                Sign in
              </Link>
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}

const strengthColors = ["", "bg-destructive", "bg-warn", "bg-accent", "bg-[color:var(--color-success)]"];
const strengthLabels = ["", "Weak", "Fair", "Strong", "Very strong"];
