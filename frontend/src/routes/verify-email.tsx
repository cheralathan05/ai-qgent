import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { useState, useEffect } from "react";
import { ApaOrb } from "@/components/apa/ApaOrb";
import { authApi } from "@/lib/api/auth";

export const Route = createFileRoute("/verify-email")({
  head: () => ({ meta: [{ title: "Verify email — APA-OS" }] }),
  component: VerifyEmailPage,
});

function VerifyEmailPage() {
  const navigate = useNavigate();
  const [status, setStatus] = useState<"loading" | "success" | "error">("loading");
  const [message, setMessage] = useState("");

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const token = params.get("token");

    if (!token) {
      setStatus("error");
      setMessage("Invalid verification link. No token provided.");
      return;
    }

    authApi.verifyEmail(token)
      .then((res) => {
        if (res.success) {
          setStatus("success");
          setMessage("Email verified successfully!");
        } else {
          setStatus("error");
          setMessage(res.message || "Verification failed.");
        }
      })
      .catch((err) => {
        setStatus("error");
        setMessage(err.response?.data?.detail || "Invalid or expired verification token.");
      });
  }, []);

  return (
    <div className="min-h-screen bg-background text-foreground grain flex items-center justify-center px-6 gradient-mesh">
      <div className="w-full max-w-[420px] transition-all duration-700 opacity-100 translate-y-0">
        <Link to="/" className="flex flex-col items-center mb-10">
          <ApaOrb size={50} state="idle" />
          <h1 className="mt-3 font-display text-[22px] tracking-tight">
            apa<span className="text-accent">·</span>os
          </h1>
        </Link>

        <div className="glass rounded-2xl p-8 text-center card-expand">
          {status === "loading" && (
            <>
              <div className="mx-auto w-14 h-14 rounded-full bg-accent/10 flex items-center justify-center mb-5">
                <svg className="animate-spin h-6 w-6 text-accent" viewBox="0 0 24 24" fill="none">
                  <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="2" opacity="0.3" />
                  <path d="M12 2a10 10 0 019.95 9" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
                </svg>
              </div>
              <h2 className="font-display text-[20px] tracking-tight">Verifying your email</h2>
              <p className="mt-2 text-[13px] text-muted-foreground">Please wait...</p>
            </>
          )}

          {status === "success" && (
            <>
              <div className="mx-auto w-14 h-14 rounded-full bg-[color:var(--color-success)]/10 flex items-center justify-center mb-5">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
                  <path d="M5 12l5 5L19 7" stroke="oklch(0.72 0.12 150)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="check-draw" style={{ strokeDasharray: 24 }} />
                </svg>
              </div>
              <h2 className="font-display text-[20px] tracking-tight">{message}</h2>
              <p className="mt-2 text-[13px] text-muted-foreground">
                You can now sign in to your account.
              </p>
              <Link
                to="/login"
                className="mt-6 inline-block text-[11px] text-accent hover:text-accent/80 transition-colors uppercase tracking-[0.18em]"
              >
                Continue to sign in
              </Link>
            </>
          )}

          {status === "error" && (
            <>
              <div className="mx-auto w-14 h-14 rounded-full bg-destructive/10 flex items-center justify-center mb-5">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <circle cx="12" cy="12" r="10" />
                  <line x1="15" y1="9" x2="9" y2="15" />
                  <line x1="9" y1="9" x2="15" y2="15" />
                </svg>
              </div>
              <h2 className="font-display text-[20px] tracking-tight">Verification failed</h2>
              <p className="mt-2 text-[13px] text-muted-foreground">{message}</p>
              <Link
                to="/login"
                className="mt-6 inline-block text-[11px] text-accent hover:text-accent/80 transition-colors uppercase tracking-[0.18em]"
              >
                Back to sign in
              </Link>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
