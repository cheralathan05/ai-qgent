import { useEffect, useRef, useState, useCallback } from "react";
import { ApaOrb } from "./ApaOrb";
import { useApa } from "@/lib/apa/store";
import { useEnt, logoutUser } from "@/lib/apa/enterprise";

/* ───────── Sign-Out Modal ───────── */

interface SignOutModalProps {
  open: boolean;
  onClose: () => void;
  onConfirm: () => void;
}

export function SignOutModal({ open, onClose, onConfirm }: SignOutModalProps) {
  const cancelRef = useRef<HTMLButtonElement>(null);
  const confirmRef = useRef<HTMLButtonElement>(null);

  const devices = useApa((s) => s.devices);
  const outcomes = useApa((s) => s.outcomes);
  const autonomy = useApa((s) => s.autonomy);
  const user = useEnt((s) => s.user);
  const workspaces = useEnt((s) => s.workspaces);
  const activeWorkspaceId = useEnt((s) => s.activeWorkspaceId);
  const memory = useApa((s) => s.memory);

  const onlineDevices = devices.filter(
    (d) => d.status === "connected" || d.status === "controlling"
  ).length;
  const activeWorkflows = outcomes.filter(
    (o) => o.currentStage !== "complete"
  ).length;
  const activeWorkspace =
    workspaces.find((w) => w.id === activeWorkspaceId)?.name ?? "Personal";

  // Focus trap + keyboard
  useEffect(() => {
    if (!open) return;
    const prev = document.activeElement as HTMLElement;
    // Small delay so the modal is in DOM
    const t = setTimeout(() => cancelRef.current?.focus(), 50);

    function onKeyDown(e: KeyboardEvent) {
      if (e.key === "Escape") {
        e.stopPropagation();
        onClose();
      }
      if (e.key === "Tab") {
        const focusable = [cancelRef.current, confirmRef.current].filter(
          Boolean
        ) as HTMLElement[];
        if (focusable.length === 0) return;
        const first = focusable[0];
        const last = focusable[focusable.length - 1];
        if (e.shiftKey && document.activeElement === first) {
          e.preventDefault();
          last.focus();
        } else if (!e.shiftKey && document.activeElement === last) {
          e.preventDefault();
          first.focus();
        }
      }
      if (e.key === "Enter" && document.activeElement === confirmRef.current) {
        e.preventDefault();
        onConfirm();
      }
    }

    document.addEventListener("keydown", onKeyDown, true);
    return () => {
      clearTimeout(t);
      document.removeEventListener("keydown", onKeyDown, true);
      prev?.focus();
    };
  }, [open, onClose, onConfirm]);

  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-[100] flex items-center justify-center px-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby="signout-title"
      aria-describedby="signout-desc"
    >
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/70 backdrop-blur-md signout-backdrop"
        onClick={onClose}
        aria-hidden="true"
      />

      {/* Modal */}
      <div className="relative w-full max-w-[480px] rounded-2xl border border-[oklch(1_0_0/0.1)] bg-[oklch(0.16_0.005_80/0.95)] backdrop-blur-xl shadow-2xl signout-modal-card">
        {/* Top glow accent */}
        <div className="absolute -top-px left-1/2 -translate-x-1/2 w-40 h-px bg-gradient-to-r from-transparent via-[oklch(0.78_0.11_70/0.5)] to-transparent" />

        <div className="px-7 pt-7 pb-6">
          {/* Header */}
          <div className="flex items-start justify-between mb-5">
            <div className="flex items-center gap-3">
              <div className="h-10 w-10 rounded-xl bg-[oklch(0.78_0.11_70/0.1)] border border-[oklch(0.78_0.11_70/0.15)] flex items-center justify-center">
                <svg
                  width="18"
                  height="18"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="oklch(0.78 0.11 70)"
                  strokeWidth="1.5"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                >
                  <path d="M9 21H5a2 2 0 01-2-2V5a2 2 0 012-2h4" />
                  <polyline points="16 17 21 12 16 7" />
                  <line x1="21" y1="12" x2="9" y2="12" />
                </svg>
              </div>
              <div>
                <h2
                  id="signout-title"
                  className="font-display text-xl tracking-tight text-[oklch(0.96_0.01_90)]"
                >
                  Leave APA-OS?
                </h2>
                <p
                  id="signout-desc"
                  className="mt-0.5 text-[11px] text-[oklch(0.65_0.015_80)]"
                >
                  End your current session
                </p>
              </div>
            </div>
            <button
              onClick={onClose}
              className="h-8 w-8 rounded-lg flex items-center justify-center text-[oklch(0.65_0.015_80)] hover:text-[oklch(0.96_0.01_90)] hover:bg-[oklch(1_0_0/0.06)] transition-all duration-200"
              aria-label="Close dialog"
            >
              <svg
                width="14"
                height="14"
                viewBox="0 0 14 14"
                fill="none"
                stroke="currentColor"
                strokeWidth="1.5"
                strokeLinecap="round"
              >
                <path d="M1 1l12 12M13 1L1 13" />
              </svg>
            </button>
          </div>

          {/* Description */}
          <p className="text-[13px] leading-relaxed text-[oklch(0.65_0.015_80)] mb-5">
            You are about to end your current session. Any running workflows
            will continue on the server. You can reconnect at any time.
          </p>

          {/* Session Info Card */}
          <div className="rounded-xl border border-[oklch(1_0_0/0.08)] bg-[oklch(0.18_0.005_80/0.6)] overflow-hidden mb-6">
            <div className="px-4 py-3 border-b border-[oklch(1_0_0/0.06)]">
              <p className="text-[9px] uppercase tracking-[0.22em] text-[oklch(0.65_0.015_80)]">
                Session Summary
              </p>
            </div>
            <div className="grid grid-cols-2 gap-px bg-[oklch(1_0_0/0.04)]">
              <SessionInfoCell
                label="Workspace"
                value={activeWorkspace}
                icon={
                  <svg
                    width="12"
                    height="12"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="1.5"
                  >
                    <rect x="3" y="3" width="7" height="7" rx="1" />
                    <rect x="14" y="3" width="7" height="7" rx="1" />
                    <rect x="3" y="14" width="7" height="7" rx="1" />
                    <rect x="14" y="14" width="7" height="7" rx="1" />
                  </svg>
                }
              />
              <SessionInfoCell
                label="Devices Online"
                value={`${onlineDevices} connected`}
                accent={onlineDevices > 0}
                icon={
                  <svg
                    width="12"
                    height="12"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="1.5"
                  >
                    <rect x="5" y="2" width="14" height="20" rx="3" />
                    <line
                      x1="12"
                      y1="18"
                      x2="12"
                      y2="18.01"
                      strokeWidth="2"
                      strokeLinecap="round"
                    />
                  </svg>
                }
              />
              <SessionInfoCell
                label="Active Workflows"
                value={`${activeWorkflows} running`}
                icon={
                  <svg
                    width="12"
                    height="12"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="1.5"
                  >
                    <polyline points="22 12 18 12 15 21 9 3 6 12 2 12" />
                  </svg>
                }
              />
              <SessionInfoCell
                label="Knowledge"
                value={`${memory.length} sources`}
                icon={
                  <svg
                    width="12"
                    height="12"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="1.5"
                  >
                    <path d="M4 19.5A2.5 2.5 0 016.5 17H20" />
                    <path d="M6.5 2H20v20H6.5A2.5 2.5 0 014 19.5v-15A2.5 2.5 0 016.5 2z" />
                  </svg>
                }
              />
              <SessionInfoCell
                label="Memory Status"
                value="Active"
                accent
                icon={
                  <svg
                    width="12"
                    height="12"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="1.5"
                  >
                    <circle cx="12" cy="12" r="10" />
                    <path d="M12 6v6l4 2" />
                  </svg>
                }
              />
              <SessionInfoCell
                label="Agent Mode"
                value={autonomy.charAt(0).toUpperCase() + autonomy.slice(1)}
                icon={
                  <svg
                    width="12"
                    height="12"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="1.5"
                  >
                    <circle cx="12" cy="12" r="3" />
                    <path d="M12 1v4M12 19v4M4.22 4.22l2.83 2.83M16.95 16.95l2.83 2.83M1 12h4M19 12h4M4.22 19.78l2.83-2.83M16.95 7.05l2.83-2.83" />
                  </svg>
                }
              />
            </div>
          </div>

          {/* Action Buttons */}
          <div className="flex gap-3">
            <button
              ref={cancelRef}
              onClick={onClose}
              className="flex-1 h-12 rounded-xl border border-[oklch(1_0_0/0.1)] bg-[oklch(1_0_0/0.04)] text-[13px] font-medium text-[oklch(0.96_0.01_90)] hover:bg-[oklch(1_0_0/0.08)] hover:border-[oklch(1_0_0/0.15)] transition-all duration-200 active:scale-[0.97]"
            >
              Stay Signed In
            </button>
            <button
              ref={confirmRef}
              onClick={onConfirm}
              className="flex-1 h-12 rounded-xl text-[13px] font-medium text-[oklch(0.14_0_0)] transition-all duration-200 active:scale-[0.97] signout-confirm-btn relative overflow-hidden group"
            >
              <span className="relative z-10 flex items-center justify-center gap-2">
                <svg
                  width="14"
                  height="14"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                >
                  <path d="M9 21H5a2 2 0 01-2-2V5a2 2 0 012-2h4" />
                  <polyline points="16 17 21 12 16 7" />
                  <line x1="21" y1="12" x2="9" y2="12" />
                </svg>
                Sign Out
              </span>
              <div className="absolute inset-0 bg-gradient-to-r from-[oklch(0.78_0.11_70)] via-[oklch(0.82_0.13_55)] to-[oklch(0.78_0.11_70)] opacity-0 group-hover:opacity-100 transition-opacity duration-200" />
              <div className="absolute inset-0 signout-confirm-glow opacity-0 group-hover:opacity-100 transition-opacity duration-300" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

function SessionInfoCell({
  label,
  value,
  accent,
  icon,
}: {
  label: string;
  value: string;
  accent?: boolean;
  icon: React.ReactNode;
}) {
  return (
    <div className="px-4 py-3 bg-[oklch(0.18_0.005_80/0.4)]">
      <div className="flex items-center gap-1.5 mb-1">
        <span className="text-[oklch(0.5_0.01_80)]">{icon}</span>
        <span className="text-[9px] uppercase tracking-[0.18em] text-[oklch(0.5_0.01_80)]">
          {label}
        </span>
      </div>
      <p
        className={`text-[12px] font-medium ${
          accent ? "text-[oklch(0.72_0.12_150)]" : "text-[oklch(0.88_0.01_90)]"
        }`}
      >
        {value}
      </p>
    </div>
  );
}

/* ───────── Sign-Out Success Animation ───────── */

interface SignOutAnimationProps {
  active: boolean;
  onDone: () => void;
}

export function SignOutAnimation({ active, onDone }: SignOutAnimationProps) {
  const [phase, setPhase] = useState<
    "idle" | "fading" | "collapsing" | "orb-shutdown" | "indicators-off" | "logo" | "done"
  >("idle");

  useEffect(() => {
    if (!active) return;
    setPhase("fading");

    const timers: ReturnType<typeof setTimeout>[] = [];

    timers.push(setTimeout(() => setPhase("collapsing"), 600));
    timers.push(setTimeout(() => setPhase("orb-shutdown"), 1200));
    timers.push(setTimeout(() => setPhase("indicators-off"), 1800));
    timers.push(setTimeout(() => setPhase("logo"), 2400));
    timers.push(
      setTimeout(() => {
        setPhase("done");
        onDone();
      }, 3600)
    );

    return () => timers.forEach(clearTimeout);
  }, [active, onDone]);

  if (!active || phase === "idle" || phase === "done") return null;

  return (
    <div
      className={`fixed inset-0 z-[200] flex flex-col items-center justify-center bg-[oklch(0.1_0_0)] transition-opacity duration-700 ${
        phase === "fading" ? "opacity-0" : "opacity-100"
      }`}
    >
      {/* Background gradient */}
      <div className="absolute inset-0 signout-bg-gradient" />

      {/* Orb shutdown */}
      <div
        className={`relative z-10 transition-all duration-1000 ease-out ${
          phase === "orb-shutdown" || phase === "indicators-off" || phase === "logo"
            ? "opacity-100 scale-100"
            : phase === "collapsing"
            ? "opacity-100 scale-90"
            : "opacity-0 scale-110"
        }`}
      >
        <ApaOrb
          size={80}
          state={
            phase === "orb-shutdown" || phase === "indicators-off" || phase === "logo"
              ? "error"
              : "success"
          }
        />
      </div>

      {/* Status indicators turning off */}
      {(phase === "indicators-off" || phase === "logo") && (
        <div className="relative z-10 mt-8 flex items-center gap-5 signout-indicators-off">
          {["Memory", "Agents", "Devices", "Knowledge"].map((label, i) => (
            <div
              key={label}
              className="flex items-center gap-2 signout-indicator"
              style={{ animationDelay: `${i * 0.1}s` }}
            >
              <span className="h-1.5 w-1.5 rounded-full bg-[oklch(0.5_0.01_80/0.3)]" />
              <span className="text-[9px] uppercase tracking-[0.18em] text-[oklch(0.5_0.01_80/0.5)]">
                {label}
              </span>
            </div>
          ))}
        </div>
      )}

      {/* Logo + Session Ended */}
      {phase === "logo" && (
        <div className="relative z-10 mt-10 text-center signout-logo-reveal">
          <div className="flex items-baseline justify-center gap-1">
            <span className="font-display text-4xl tracking-tight text-[oklch(0.96_0.01_90)]">
              apa
            </span>
            <span className="font-display text-4xl text-[oklch(0.78_0.11_70)]">
              ·
            </span>
            <span className="font-display text-4xl tracking-tight text-[oklch(0.96_0.01_90)]">
              os
            </span>
          </div>
          <div className="mt-5 space-y-1">
            <p className="text-[14px] font-display tracking-tight text-[oklch(0.88_0.01_90)]">
              Session Ended
            </p>
            <p className="text-[12px] text-[oklch(0.5_0.01_80)]">
              See you again soon.
            </p>
          </div>
        </div>
      )}
    </div>
  );
}

/* ───────── Sign-Out Button (Sidebar) ───────── */

interface SignOutButtonProps {
  onClick: () => void;
}

export function SignOutButton({ onClick }: SignOutButtonProps) {
  const [hovered, setHovered] = useState(false);

  return (
    <button
      onClick={onClick}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      className="w-full h-12 rounded-xl flex items-center gap-3 px-4 text-left transition-all duration-200 group relative overflow-hidden signout-sidebar-btn"
      aria-label="Sign out of APA-OS"
      role="button"
    >
      {/* Glass background */}
      <div className="absolute inset-0 rounded-xl bg-[oklch(0.18_0.005_80/0.5)] backdrop-blur-xl border border-[oklch(1_0_0/0.08)] transition-all duration-200 group-hover:border-[oklch(0.78_0.11_70/0.25)] group-hover:bg-[oklch(0.2_0.006_80/0.6)]" />

      {/* Hover glow */}
      <div
        className={`absolute inset-0 rounded-xl transition-opacity duration-300 pointer-events-none ${
          hovered ? "opacity-100" : "opacity-0"
        }`}
        style={{
          boxShadow:
            "0 0 0 1px oklch(0.78 0.11 70 / 0.2), 0 0 24px -4px oklch(0.78 0.11 70 / 0.15)",
        }}
      />

      {/* Icon */}
      <div className="relative z-10 h-7 w-7 rounded-lg bg-[oklch(0.78_0.11_70/0.08)] border border-[oklch(0.78_0.11_70/0.12)] flex items-center justify-center transition-all duration-200 group-hover:bg-[oklch(0.78_0.11_70/0.12)] group-hover:border-[oklch(0.78_0.11_70/0.2)]">
        <svg
          width="13"
          height="13"
          viewBox="0 0 24 24"
          fill="none"
          stroke="oklch(0.78 0.11 70)"
          strokeWidth="1.5"
          strokeLinecap="round"
          strokeLinejoin="round"
          className="transition-transform duration-200 group-hover:translate-x-0.5"
        >
          <path d="M9 21H5a2 2 0 01-2-2V5a2 2 0 012-2h4" />
          <polyline points="16 17 21 12 16 7" />
          <line x1="21" y1="12" x2="9" y2="12" />
        </svg>
      </div>

      {/* Text */}
      <div className="relative z-10 flex-1 min-w-0">
        <p className="text-[12px] font-medium text-[oklch(0.88_0.01_90)] group-hover:text-[oklch(0.96_0.01_90)] transition-colors duration-200">
          Sign Out
        </p>
        <p className="text-[9px] text-[oklch(0.5_0.01_80)] group-hover:text-[oklch(0.6_0.01_80)] transition-colors duration-200">
          End Current Session
        </p>
      </div>

      {/* Chevron */}
      <svg
        width="12"
        height="12"
        viewBox="0 0 24 24"
        fill="none"
        stroke="oklch(0.5 0.01 80)"
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
        className="relative z-10 transition-all duration-200 group-hover:stroke-[oklch(0.78_0.11_70)] group-hover:translate-x-0.5"
      >
        <polyline points="9 18 15 12 9 6" />
      </svg>

      {/* Press effect */}
      <div className="absolute inset-0 rounded-xl bg-[oklch(0.78_0.11_70/0.08)] opacity-0 active:opacity-100 transition-opacity duration-100 pointer-events-none" />
    </button>
  );
}
