import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { useState, useEffect } from "react";
import { ApaOrb } from "@/components/apa/ApaOrb";

export const Route = createFileRoute("/verify-device")({
  head: () => ({ meta: [{ title: "Verify Device — APA-OS" }] }),
  component: VerifyDevicePage,
});

const VERIFY_CHECKS = [
  { id: "fingerprint", label: "Device Fingerprint", detail: "Confirming unique device identity" },
  { id: "adb", label: "ADB Authorization", detail: "Verifying Android Debug Bridge access" },
  { id: "channel", label: "Secure Channel", detail: "Establishing encrypted communication" },
  { id: "capabilities", label: "Capability Audit", detail: "Scanning available device features" },
  { id: "agent", label: "Agent Handshake", detail: "Connecting APA-OS Agent service" },
];

function VerifyDevicePage() {
  const navigate = useNavigate();
  const [currentCheck, setCurrentCheck] = useState(-1);
  const [completed, setCompleted] = useState<string[]>([]);
  const [allDone, setAllDone] = useState(false);
  const [mounted, setMounted] = useState(false);

  useEffect(() => { setMounted(true); }, []);

  useEffect(() => {
    if (currentCheck >= VERIFY_CHECKS.length) {
      setAllDone(true);
      return;
    }
    if (currentCheck < 0) {
      const t = setTimeout(() => setCurrentCheck(0), 500);
      return () => clearTimeout(t);
    }
    const t = setTimeout(() => {
      setCompleted((c) => [...c, VERIFY_CHECKS[currentCheck].id]);
      setCurrentCheck((i) => i + 1);
    }, 800 + Math.random() * 600);
    return () => clearTimeout(t);
  }, [currentCheck]);

  return (
    <div className="min-h-screen bg-background text-foreground grain flex items-center justify-center px-6 gradient-mesh">
      <div className={`w-full max-w-[480px] transition-all duration-700 ${mounted ? "opacity-100 translate-y-0" : "opacity-0 translate-y-6"}`}>
        {/* Header */}
        <div className="text-center mb-8">
          <div className="mx-auto mb-5">
            <ApaOrb size={70} state={allDone ? "success" : "thinking"} />
          </div>
          <p className="text-[10px] uppercase tracking-[0.28em] text-accent mb-3">Device Verification</p>
          <h1 className="font-display text-[28px] tracking-tight">
            {allDone ? "Verification Complete" : "Verifying your device…"}
          </h1>
          <p className="mt-2 text-[13px] text-muted-foreground">
            {allDone
              ? "Your device identity has been confirmed."
              : "Confirming device identity and establishing secure connection."
            }
          </p>
        </div>

        {/* Checks */}
        <div className="glass rounded-2xl p-6 mb-6">
          <div className="space-y-3">
            {VERIFY_CHECKS.map((check, i) => {
              const isDone = completed.includes(check.id);
              const isCurrent = currentCheck === i;
              return (
                <div
                  key={check.id}
                  className={`flex items-center gap-4 px-4 py-3 rounded-xl transition-all duration-300 ${
                    isDone
                      ? "bg-[color:var(--color-success)]/5 border border-[color:var(--color-success)]/20"
                      : isCurrent
                      ? "bg-accent/5 border border-accent/20"
                      : "bg-surface/30 border border-transparent"
                  }`}
                >
                  <div className={`w-7 h-7 rounded-full flex items-center justify-center shrink-0 transition-all duration-300 ${
                    isDone
                      ? "bg-[color:var(--color-success)]"
                      : isCurrent
                      ? "bg-accent"
                      : "bg-surface border hairline"
                  }`}>
                    {isDone ? (
                      <svg width="12" height="10" viewBox="0 0 12 10" fill="none">
                        <path d="M1 5L4 8L11 1" stroke="oklch(0.14 0 0)" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
                      </svg>
                    ) : isCurrent ? (
                      <svg className="animate-spin h-3 w-3" viewBox="0 0 12 12" fill="none">
                        <circle cx="6" cy="6" r="5" stroke="oklch(0.14 0 0)" strokeWidth="1.5" opacity="0.3" />
                        <path d="M6 1a5 5 0 014.95 4" stroke="oklch(0.14 0 0)" strokeWidth="1.5" strokeLinecap="round" />
                      </svg>
                    ) : (
                      <span className="text-[9px] font-mono text-muted-foreground">{i + 1}</span>
                    )}
                  </div>
                  <div className="flex-1">
                    <p className={`text-[12px] ${isDone ? "text-foreground" : isCurrent ? "text-foreground" : "text-muted-foreground"}`}>
                      {check.label}
                    </p>
                    <p className="text-[10px] text-muted-foreground">{check.detail}</p>
                  </div>
                  <span className={`text-[9px] font-mono uppercase tracking-wider ${
                    isDone ? "text-[color:var(--color-success)]" : isCurrent ? "text-accent" : "text-muted-foreground/40"
                  }`}>
                    {isDone ? "passed" : isCurrent ? "checking…" : "pending"}
                  </span>
                </div>
              );
            })}
          </div>
        </div>

        {/* Progress */}
        <div className="mb-6">
          <div className="flex items-center justify-between mb-2">
            <span className="text-[10px] uppercase tracking-[0.18em] text-muted-foreground">Progress</span>
            <span className="text-[11px] font-mono text-accent">{completed.length}/{VERIFY_CHECKS.length}</span>
          </div>
          <div className="h-1.5 bg-[var(--color-border)] rounded-full overflow-hidden">
            <div
              className="h-full bg-accent rounded-full transition-all duration-500 ease-out"
              style={{ width: `${(completed.length / VERIFY_CHECKS.length) * 100}%` }}
            />
          </div>
        </div>

        {/* CTA */}
        {allDone && (
          <Link
            to="/setup-check"
            className="block w-full py-3.5 rounded-xl bg-accent text-accent-foreground text-[12px] uppercase tracking-[0.22em] font-medium text-center hover:brightness-110 hover:shadow-[0_0_30px_-4px_oklch(0.78_0.11_70/0.4)] transition-all btn-pulse card-expand"
          >
            Continue to AI Readiness →
          </Link>
        )}
      </div>
    </div>
  );
}
