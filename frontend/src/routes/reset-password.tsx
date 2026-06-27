import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { useState, useEffect } from "react";
import { ApaOrb } from "@/components/apa/ApaOrb";
import { authApi } from "@/lib/api/auth";
import { AxiosError } from "axios";

export const Route = createFileRoute("/reset-password")({
  head: () => ({ meta: [{ title: "Set new password — APA-OS" }] }),
  component: ResetPasswordPage,
});

function ResetPasswordPage() {
  const navigate = useNavigate();
  const [pw, setPw] = useState("");
  const [confirmPw, setConfirmPw] = useState("");
  const [showPw, setShowPw] = useState(false);
  const [loading, setLoading] = useState(false);
  const [mounted, setMounted] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);
  const [token, setToken] = useState<string | null>(null);

  useEffect(() => {
    setMounted(true);
    const params = new URLSearchParams(window.location.search);
    const t = params.get("token");
    if (!t) {
      setError("Invalid reset link. No token provided.");
    }
    setToken(t);
  }, []);

  const canSubmit = pw.length >= 6 && pw === confirmPw && !!token;

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!canSubmit || !token) return;
    setLoading(true);
    setError(null);
    try {
      const res = await authApi.resetPassword(token, pw);
      if (res.success) {
        setSuccess(true);
      }
    } catch (err) {
      const axiosErr = err as AxiosError<{ detail: string }>;
      if (axiosErr.response?.data?.detail) {
        setError(axiosErr.response.data.detail);
      } else {
        setError("Something went wrong. Please try again.");
      }
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen bg-background text-foreground grain flex items-center justify-center px-6 gradient-mesh">
      <div className={`w-full max-w-[420px] transition-all duration-700 ${mounted ? "opacity-100 translate-y-0" : "opacity-0 translate-y-6"}`}>
        <Link to="/" className="flex flex-col items-center mb-10">
          <ApaOrb size={50} state="idle" />
          <h1 className="mt-3 font-display text-[22px] tracking-tight">
            apa<span className="text-accent">·</span>os
          </h1>
        </Link>

        {success ? (
          <div className="glass rounded-2xl p-8 text-center card-expand">
            <div className="mx-auto w-14 h-14 rounded-full bg-[color:var(--color-success)]/10 flex items-center justify-center mb-5">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
                <path d="M5 12l5 5L19 7" stroke="oklch(0.72 0.12 150)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="check-draw" style={{ strokeDasharray: 24 }} />
              </svg>
            </div>
            <h2 className="font-display text-[20px] tracking-tight">Password changed</h2>
            <p className="mt-2 text-[13px] text-muted-foreground">
              Your password has been reset successfully.
            </p>
            <Link
              to="/login"
              className="mt-6 inline-block text-[11px] text-accent hover:text-accent/80 transition-colors uppercase tracking-[0.18em]"
            >
              Sign in with new password
            </Link>
          </div>
        ) : (
          <>
            <h1 className="font-display text-[28px] tracking-tight text-center">Set new password.</h1>
            <p className="mt-2 text-[13px] text-muted-foreground text-center">
              Enter your new password below.
            </p>

            {error && (
              <div className="mt-4 p-3 rounded-xl bg-destructive/10 border border-destructive/30 text-[12px] text-destructive">
                {error}
              </div>
            )}

            <form onSubmit={handleSubmit} className="mt-8 space-y-5">
              <div className="relative">
                <label className="block">
                  <span className="text-[9px] uppercase tracking-[0.22em] text-muted-foreground">
                    New password
                  </span>
                  <div className="relative mt-2">
                    <input
                      type={showPw ? "text" : "password"}
                      value={pw}
                      onChange={(e) => setPw(e.target.value)}
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
              </div>

              <div className="relative">
                <label className="block">
                  <span className="text-[9px] uppercase tracking-[0.22em] text-muted-foreground">
                    Confirm new password
                  </span>
                  <input
                    type={showPw ? "text" : "password"}
                    value={confirmPw}
                    onChange={(e) => setConfirmPw(e.target.value)}
                    placeholder="Re-enter password"
                    className={`mt-2 w-full bg-transparent border rounded-xl px-4 py-3 text-[14px] outline-none input-glow transition-all duration-200 placeholder:text-muted-foreground/30 ${
                      confirmPw.length > 0 && pw === confirmPw
                        ? "border-[color:var(--color-success)]"
                        : confirmPw.length > 0 && pw !== confirmPw
                        ? "border-destructive"
                        : "hairline focus:border-accent"
                    }`}
                    autoComplete="new-password"
                  />
                </label>
                {confirmPw.length > 0 && pw === confirmPw && (
                  <span className="absolute right-3 top-[38px] text-[color:var(--color-success)]">
                    <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
                      <path d="M3 7L6 10L11 4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
                    </svg>
                  </span>
                )}
              </div>

              <button
                type="submit"
                disabled={!canSubmit || loading || !token}
                className="w-full py-3.5 rounded-xl bg-accent text-accent-foreground text-[12px] uppercase tracking-[0.22em] font-medium transition-all duration-300 disabled:opacity-40 disabled:cursor-not-allowed hover:brightness-110 hover:shadow-[0_0_30px_-4px_oklch(0.78_0.11_70/0.4)] active:scale-[0.98]"
              >
                {loading ? (
                  <span className="flex items-center justify-center gap-2">
                    <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24" fill="none">
                      <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="2" opacity="0.3" />
                      <path d="M12 2a10 10 0 019.95 9" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
                    </svg>
                    Resetting…
                  </span>
                ) : (
                  "Reset password"
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
