import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { useState, useEffect } from "react";
import { ApaOrb } from "@/components/apa/ApaOrb";

export const Route = createFileRoute("/setup-check")({
  head: () => ({ meta: [{ title: "AI Readiness — APA-OS" }] }),
  component: SetupCheckPage,
});

interface CheckItem {
  id: string;
  label: string;
  detail: string;
  status: "pending" | "pass" | "warning" | "failed";
}

const INITIAL_CHECKS: Omit<CheckItem, "status">[] = [
  { id: "adb", label: "ADB Connected", detail: "Android Debug Bridge connection active" },
  { id: "trust", label: "Device Trusted", detail: "Device authorized for AI control" },
  { id: "battery", label: "Battery Available", detail: "Sufficient battery for operations" },
  { id: "foreground", label: "Foreground App Detection", detail: "Can detect current app" },
  { id: "screenshot", label: "Screenshot Capability", detail: "Screen capture enabled" },
  { id: "ocr", label: "OCR Capability", detail: "Text recognition from screenshots" },
  { id: "navigation", label: "Navigation Capability", detail: "Swipe, tap, scroll gestures" },
  { id: "knowledge", label: "Knowledge Capability", detail: "Access to knowledge base" },
];

function SetupCheckPage() {
  const navigate = useNavigate();
  const [checks, setChecks] = useState<CheckItem[]>(INITIAL_CHECKS.map((c) => ({ ...c, status: "pending" as const })));
  const [currentIdx, setCurrentIdx] = useState(-1);
  const [mounted, setMounted] = useState(false);
  const [allDone, setAllDone] = useState(false);

  useEffect(() => { setMounted(true); }, []);

  // Run checks sequentially
  useEffect(() => {
    if (currentIdx < 0) {
      const t = setTimeout(() => setCurrentIdx(0), 600);
      return () => clearTimeout(t);
    }
    if (currentIdx >= INITIAL_CHECKS.length) {
      setAllDone(true);
      return;
    }

    const t = setTimeout(() => {
      // Simulate check result (mostly pass, one warning)
      const result: CheckItem["status"] =
        INITIAL_CHECKS[currentIdx].id === "battery" ? "warning"
        : INITIAL_CHECKS[currentIdx].id === "knowledge" ? "warning"
        : "pass";

      setChecks((prev) =>
        prev.map((c, i) => (i === currentIdx ? { ...c, status: result } : c))
      );
      setCurrentIdx((i) => i + 1);
    }, 500 + Math.random() * 500);

    return () => clearTimeout(t);
  }, [currentIdx]);

  const passedCount = checks.filter((c) => c.status === "pass").length;
  const warningCount = checks.filter((c) => c.status === "warning").length;
  const failedCount = checks.filter((c) => c.status === "failed").length;
  const score = Math.round(((passedCount * 100 + warningCount * 60) / (INITIAL_CHECKS.length * 100)) * 100);

  const circumference = 2 * Math.PI * 42;
  const dashOffset = circumference - (score / 100) * circumference;

  return (
    <div className="min-h-screen bg-background text-foreground grain flex items-center justify-center px-6 gradient-mesh">
      <div className={`w-full max-w-[520px] transition-all duration-700 ${mounted ? "opacity-100 translate-y-0" : "opacity-0 translate-y-6"}`}>
        {/* Header */}
        <div className="text-center mb-8">
          <div className="mx-auto mb-5">
            <ApaOrb size={70} state={allDone ? (failedCount > 0 ? "error" : "success") : "thinking"} />
          </div>
          <p className="text-[10px] uppercase tracking-[0.28em] text-accent mb-3">AI Readiness Check</p>
          <h1 className="font-display text-[28px] tracking-tight">
            {allDone ? (failedCount > 0 ? "Almost Ready" : "System Ready") : "Checking capabilities…"}
          </h1>
          <p className="mt-2 text-[13px] text-muted-foreground">
            {allDone
              ? "Verifying all AI capabilities are operational."
              : "Running diagnostic checks on your connected device."
            }
          </p>
        </div>

        {/* Progress Ring */}
        {allDone && (
          <div className="flex justify-center mb-8 card-expand">
            <div className="relative">
              <svg width="120" height="120" viewBox="0 0 100 100" className="score-count">
                {/* Background ring */}
                <circle
                  cx="50" cy="50" r="42"
                  fill="none"
                  stroke="oklch(1 0 0 / 0.06)"
                  strokeWidth="4"
                />
                {/* Progress ring */}
                <circle
                  cx="50" cy="50" r="42"
                  fill="none"
                  stroke={score >= 90 ? "oklch(0.72 0.12 150)" : score >= 70 ? "oklch(0.78 0.11 70)" : "oklch(0.62 0.18 25)"}
                  strokeWidth="4"
                  strokeLinecap="round"
                  strokeDasharray={circumference}
                  strokeDashoffset={dashOffset}
                  transform="rotate(-90 50 50)"
                  className="ring-fill"
                />
              </svg>
              <div className="absolute inset-0 flex flex-col items-center justify-center">
                <span className="font-display text-[28px] leading-none">{score}</span>
                <span className="text-[9px] uppercase tracking-[0.15em] text-muted-foreground mt-1">Readiness</span>
              </div>
            </div>
          </div>
        )}

        {/* Checks */}
        <div className="glass rounded-2xl p-6 mb-6">
          <div className="space-y-2">
            {checks.map((check, i) => (
              <div
                key={check.id}
                className={`flex items-center gap-4 px-4 py-3 rounded-xl transition-all duration-300 ${
                  check.status === "pass"
                    ? "bg-[color:var(--color-success)]/5"
                    : check.status === "warning"
                    ? "bg-warn/5"
                    : check.status === "failed"
                    ? "bg-destructive/5"
                    : currentIdx === i
                    ? "bg-accent/5"
                    : "bg-surface/20"
                }`}
              >
                {/* Status icon */}
                <div className={`w-6 h-6 rounded-full flex items-center justify-center shrink-0 transition-all duration-300 ${
                  check.status === "pass"
                    ? "bg-[color:var(--color-success)]"
                    : check.status === "warning"
                    ? "bg-warn"
                    : check.status === "failed"
                    ? "bg-destructive"
                    : currentIdx === i
                    ? "bg-accent"
                    : "bg-surface border hairline"
                }`}>
                  {check.status === "pass" && (
                    <svg width="10" height="8" viewBox="0 0 10 8" fill="none">
                      <path d="M1 4L3.5 6.5L9 1" stroke="oklch(0.14 0 0)" strokeWidth="1.5" strokeLinecap="round" />
                    </svg>
                  )}
                  {check.status === "warning" && (
                    <span className="text-[10px] font-bold text-background">!</span>
                  )}
                  {check.status === "failed" && (
                    <svg width="8" height="8" viewBox="0 0 8 8" fill="none">
                      <path d="M1 1L7 7M7 1L1 7" stroke="oklch(0.98 0 0)" strokeWidth="1.5" strokeLinecap="round" />
                    </svg>
                  )}
                  {check.status === "pending" && currentIdx !== i && (
                    <span className="text-[9px] font-mono text-muted-foreground/60">{i + 1}</span>
                  )}
                  {currentIdx === i && check.status === "pending" && (
                    <svg className="animate-spin h-3 w-3" viewBox="0 0 12 12" fill="none">
                      <circle cx="6" cy="6" r="5" stroke="oklch(0.14 0 0)" strokeWidth="1.5" opacity="0.3" />
                      <path d="M6 1a5 5 0 014.95 4" stroke="oklch(0.14 0 0)" strokeWidth="1.5" strokeLinecap="round" />
                    </svg>
                  )}
                </div>

                {/* Label */}
                <div className="flex-1 min-w-0">
                  <p className={`text-[12px] ${
                    check.status !== "pending" ? "text-foreground" : currentIdx === i ? "text-foreground" : "text-muted-foreground"
                  }`}>
                    {check.label}
                  </p>
                  <p className="text-[10px] text-muted-foreground truncate">{check.detail}</p>
                </div>

                {/* Status text */}
                <span className={`text-[9px] font-mono uppercase tracking-wider shrink-0 ${
                  check.status === "pass" ? "text-[color:var(--color-success)]"
                  : check.status === "warning" ? "text-warn"
                  : check.status === "failed" ? "text-destructive"
                  : currentIdx === i ? "text-accent"
                  : "text-muted-foreground/40"
                }`}>
                  {check.status === "pass" ? "pass" : check.status === "warning" ? "warn" : check.status === "failed" ? "fail" : currentIdx === i ? "checking…" : "pending"}
                </span>
              </div>
            ))}
          </div>
        </div>

        {/* Summary */}
        {allDone && (
          <div className="flex items-center justify-center gap-6 mb-6 card-expand" style={{ animationDelay: "0.2s" }}>
            {[
              { count: passedCount, label: "Passed", color: "text-[color:var(--color-success)]" },
              { count: warningCount, label: "Warnings", color: "text-warn" },
              { count: failedCount, label: "Failed", color: "text-destructive" },
            ].map((s) => (
              <div key={s.label} className="text-center">
                <p className={`font-display text-[22px] ${s.color}`}>{s.count}</p>
                <p className="text-[9px] uppercase tracking-[0.15em] text-muted-foreground">{s.label}</p>
              </div>
            ))}
          </div>
        )}

        {/* CTA */}
        {allDone && (
          <Link
            to="/ready"
            className="block w-full py-3.5 rounded-xl bg-accent text-accent-foreground text-[12px] uppercase tracking-[0.22em] font-medium text-center hover:brightness-110 hover:shadow-[0_0_30px_-4px_oklch(0.78_0.11_70/0.4)] transition-all btn-pulse card-expand"
            style={{ animationDelay: "0.4s" }}
          >
            {failedCount > 0 ? "Continue Anyway →" : "Proceed to Dashboard →"}
          </Link>
        )}
      </div>
    </div>
  );
}
