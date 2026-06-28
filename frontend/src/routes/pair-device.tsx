import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { useState, useEffect, useCallback } from "react";
import { ApaOrb } from "@/components/apa/ApaOrb";
import { useDevicePairing, type PairingState } from "@/hooks/useDevicePairing";
import type { USBDeviceInfo } from "@/lib/api/pairing";

export const Route = createFileRoute("/pair-device")({
  head: () => ({ meta: [{ title: "Pair Device — APA-OS" }] }),
  component: PairDevicePage,
});

type PairingMethod = "usb" | "wireless" | "qr";

const STEPS = [
  { key: "discover", label: "Discover", detail: "Find your device" },
  { key: "connect", label: "Connect", detail: "Establish link" },
  { key: "verify", label: "Verify", detail: "Confirm identity" },
  { key: "trust", label: "Trust", detail: "Authorize access" },
  { key: "permissions", label: "Permissions", detail: "Grant capabilities" },
  { key: "ready", label: "Ready", detail: "AI connected" },
] as const;

const STEP_ORDER: Record<string, number> = {
  idle: -1, discovering: 0, connecting: 1, verifying: 2,
  trusting: 3, permissions: 4, registering: 4, twin_creating: 4, ready: 5, error: -1,
};

function PairDevicePage() {
  const navigate = useNavigate();
  const pairing = useDevicePairing();
  const [method, setMethod] = useState<PairingMethod | null>(null);
  const [mounted, setMounted] = useState(false);
  const [pairCode] = useState(() => Math.random().toString(36).slice(2, 8).toUpperCase());
  const [wirelessIp, setWirelessIp] = useState("");
  const [wirelessPort, setWirelessPort] = useState("5555");
  const [wirelessCode, setWirelessCode] = useState("");
  const [permissionsGranted, setPermissionsGranted] = useState(false);

  useEffect(() => { setMounted(true); }, []);

  // Check pairing status on mount
  useEffect(() => {
    pairing.checkStatus();
  }, []);

  // Determine current step index from workflow state
  const currentStepIdx = STEP_ORDER[pairing.step] ?? 0;
  const stepIdx = Math.max(0, Math.min(currentStepIdx, STEPS.length - 1));

  // Connect WebSocket when ready
  useEffect(() => {
    if (pairing.step === 'ready') {
      pairing.connectWebSocket();
    }
  }, [pairing.step]);

  const dev = pairing.deviceInfo;

  return (
    <div className="min-h-screen bg-background text-foreground grain">
      <header className="border-b hairline px-6 lg:px-10 py-6">
        <div className="max-w-[1400px] mx-auto flex items-center justify-between">
          <Link to="/" className="flex items-center gap-2">
            <ApaOrb size={28} state={pairing.step === 'ready' ? 'success' : pairing.loading ? 'thinking' : 'idle'} />
            <span className="font-display text-[18px] tracking-tight">apa<span className="text-accent">·</span>os</span>
          </Link>
          <div className="flex items-center gap-3">
            <span className="text-[10px] uppercase tracking-[0.18em] text-muted-foreground">
              Device Pairing Center
            </span>
            <Link
              to="/dashboard"
              className="text-[11px] text-muted-foreground hover:text-foreground transition-colors uppercase tracking-[0.18em]"
            >
              Skip →
            </Link>
          </div>
        </div>
      </header>

      <div className="max-w-[1400px] mx-auto px-6 lg:px-10 py-8">
        <div className={`mb-8 transition-all duration-700 ${mounted ? "opacity-100 translate-y-0" : "opacity-0 translate-y-4"}`}>
          <p className="text-[10px] uppercase tracking-[0.28em] text-accent mb-3">Device Pairing Center</p>
          <h1 className="font-display text-[36px] lg:text-[44px] tracking-tight leading-[1.02]">
            {pairing.step === 'ready' ? 'Device connected.' : 'Connect your phone.'}
          </h1>
          <p className="mt-3 text-[14px] text-muted-foreground max-w-[500px] leading-relaxed">
            {pairing.step === 'error'
              ? `Error: ${pairing.error}`
              : pairing.step === 'ready'
              ? `${dev?.device_name || dev?.model || 'Device'} is paired and ready for AI control.`
              : 'Connect your Android device via USB. APA-OS automatically discovers and pairs.'}
          </p>
        </div>

        {/* Step Progress */}
        <div className={`mb-8 transition-all duration-500 ${mounted ? "opacity-100" : "opacity-0"}`} style={{ transitionDelay: "200ms" }}>
          <div className="flex items-center gap-0">
            {STEPS.map((s, i) => (
              <div key={s.key} className="flex items-center">
                <div className="flex flex-col items-center">
                  <div className={`w-8 h-8 rounded-full flex items-center justify-center text-[11px] font-mono transition-all duration-300 ${
                    i < stepIdx
                      ? "bg-[color:var(--color-success)] text-background"
                      : i === stepIdx
                      ? "bg-accent text-accent-foreground"
                      : "bg-surface border hairline text-muted-foreground"
                  }`}>
                    {i < stepIdx ? (
                      <svg width="12" height="10" viewBox="0 0 12 10" fill="none">
                        <path d="M1 5L4 8L11 1" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
                      </svg>
                    ) : (
                      String(i + 1)
                    )}
                  </div>
                  <span className={`mt-1.5 text-[9px] uppercase tracking-[0.15em] transition-colors ${
                    i <= stepIdx ? "text-foreground" : "text-muted-foreground/50"
                  }`}>{s.label}</span>
                </div>
                {i < STEPS.length - 1 && (
                  <div className={`w-12 lg:w-20 h-px mx-1 mb-5 transition-colors duration-300 ${
                    i < stepIdx ? "bg-[color:var(--color-success)]" : "bg-[var(--color-border)]"
                  }`} />
                )}
              </div>
            ))}
          </div>
        </div>

        <div className="grid lg:grid-cols-[1fr_380px] gap-6">
          {/* Left: Main pairing area */}
          <div className={`transition-all duration-500 ${mounted ? "opacity-100 translate-y-0" : "opacity-0 translate-y-4"}`} style={{ transitionDelay: "300ms" }}>
            {/* Method Selection */}
            {!method && pairing.step === 'idle' && (
              <MethodSelection onSelect={(m) => { setMethod(m); pairing.discoverUSB(); }} />
            )}

            {/* Error state */}
            {pairing.step === 'error' && (
              <div className="glass rounded-2xl p-6 slide-in-up">
                <div className="flex items-center gap-3 mb-4">
                  <div className="h-8 w-8 rounded-full bg-red-500/10 flex items-center justify-center">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#ef4444" strokeWidth="1.5">
                      <circle cx="12" cy="12" r="10" />
                      <line x1="12" y1="8" x2="12" y2="12" />
                      <line x1="12" y1="16" x2="12.01" y2="16" />
                    </svg>
                  </div>
                  <div>
                    <p className="text-[13px] font-medium text-red-500">Pairing Error</p>
                    <p className="text-[11px] text-muted-foreground">{pairing.error}</p>
                  </div>
                </div>
                <button
                  onClick={() => { pairing.discoverUSB(); }}
                  className="w-full py-3 rounded-xl bg-accent text-accent-foreground text-[11px] uppercase tracking-[0.22em] font-medium hover:brightness-110 transition-all"
                >
                  Retry
                </button>
              </div>
            )}

            {/* USB Discovery */}
            {method === "usb" && pairing.step !== 'ready' && pairing.step !== 'error' && (
              <USBDiscoveryPanel
                pairing={pairing}
                onRetry={() => pairing.discoverUSB()}
              />
            )}

            {/* Verify */}
            {pairing.step === 'verifying' && (
              <VerifyPanel pairing={pairing} />
            )}

            {/* Trust */}
            {pairing.step === 'trusting' && dev && (
              <TrustPanel pairing={pairing} deviceName={dev.device_name || dev.model || 'Device'} />
            )}

            {/* Permissions */}
            {pairing.step === 'permissions' && (
              <PermissionsPanel
                onGrant={() => {
                  setPermissionsGranted(true);
                  if (pairing.deviceId) {
                    pairing.syncPermissions(pairing.deviceId);
                  }
                }}
                granted={permissionsGranted}
                onContinue={async () => {
                  if (pairing.serial) {
                    await pairing.registerDevice(pairing.serial);
                    await pairing.createTwin(pairing.serial);
                  }
                }}
                loading={pairing.loading}
              />
            )}

            {/* Ready */}
            {pairing.step === 'ready' && (
              <ReadyPanel
                deviceName={dev?.device_name || dev?.model || 'Device'}
                capabilities={pairing.twin?.capabilities || [
                  'Screenshot', 'Navigation', 'OCR', 'App Control', 'Notifications', 'File Access',
                ]}
                readinessScore={pairing.twin?.readiness_score || 98}
              />
            )}
          </div>

          {/* Right: Live Device Status */}
          <aside className={`space-y-4 transition-all duration-500 ${mounted ? "opacity-100 translate-y-0" : "opacity-0 translate-y-4"}`} style={{ transitionDelay: "400ms" }}>
            {(() => {
              const showLive = pairing.step !== 'idle' && pairing.step !== 'error';
              if (!showLive) return null;
              return (
                <LiveDeviceCard
                  deviceName={dev?.device_name || dev?.model || 'Android Device'}
                  model={dev?.model || ''}
                  manufacturer={dev?.manufacturer || ''}
                  android={dev?.android_version || ''}
                  battery={dev?.battery_percentage ?? pairing.liveHeartbeat?.battery_level ?? 0}
                  charging={dev?.charging ?? pairing.liveHeartbeat?.battery_charging ?? false}
                  serial={dev?.serial || ''}
                  screen={`${dev?.screen_width || 0} × ${dev?.screen_height || 0}`}
                  foreground={pairing.liveHeartbeat?.foreground_app || dev?.foreground_app || ''}
                  lockState={pairing.liveHeartbeat?.lock_state || dev?.lock_state || 'unknown'}
                  online={pairing.isOnline}
                  connected={pairing.step === 'ready'}
                  scanning={pairing.step === 'discovering'}
                />
              );
            })()}

            <ConnectionStatusPanel
              method={method}
              connected={pairing.step === 'ready' || pairing.step === 'twin_creating' || pairing.step === 'registering'}
              verified={pairing.step === 'verifying' || STEP_ORDER[pairing.step] >= 2}
              trusted={pairing.step === 'trusting' || STEP_ORDER[pairing.step] >= 3}
              aiReady={pairing.step === 'ready'}
            />
          </aside>
        </div>
      </div>
    </div>
  );
}

/* ─── Method Selection ─── */
function MethodSelection({ onSelect }: { onSelect: (m: PairingMethod) => void }) {
  return (
    <div className="space-y-4 slide-in-up">
      <p className="text-[10px] uppercase tracking-[0.22em] text-muted-foreground mb-4">Choose pairing method</p>
      <div className="grid sm:grid-cols-3 gap-4">
        {[
          { id: "usb" as const, title: "USB Pairing", detail: "Connect via cable for instant pairing", icon: (
            <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.2">
              <rect x="5" y="2" width="14" height="20" rx="3" />
              <line x1="12" y1="18" x2="12" y2="18.01" strokeWidth="2" strokeLinecap="round" />
            </svg>
          )},
          { id: "wireless" as const, title: "Wireless ADB", detail: "Pair over network with code", icon: (
            <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.2">
              <path d="M5 12.55a11 11 0 0114.08 0" />
              <path d="M1.42 9a16 16 0 0121.16 0" />
              <path d="M8.53 16.11a6 6 0 016.95 0" />
              <circle cx="12" cy="20" r="1" fill="currentColor" />
            </svg>
          )},
          { id: "qr" as const, title: "QR Code", detail: "Scan with APA-OS Agent app", icon: (
            <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.2">
              <rect x="3" y="3" width="7" height="7" rx="1" />
              <rect x="14" y="3" width="7" height="7" rx="1" />
              <rect x="3" y="14" width="7" height="7" rx="1" />
              <rect x="14" y="14" width="3" height="3" />
              <rect x="18" y="18" width="3" height="3" />
            </svg>
          )},
        ].map((m) => (
          <button
            key={m.id}
            onClick={() => onSelect(m.id)}
            className="glass rounded-2xl p-6 text-left hover-lift hover-glow transition-all duration-300 group"
          >
            <div className="text-accent mb-4 group-hover:scale-110 transition-transform duration-300">{m.icon}</div>
            <p className="text-[14px] font-medium">{m.title}</p>
            <p className="mt-1 text-[11px] text-muted-foreground">{m.detail}</p>
          </button>
        ))}
      </div>
    </div>
  );
}

/* ─── USB Discovery Panel ─── */
function USBDiscoveryPanel({ pairing, onRetry }: { pairing: ReturnType<typeof useDevicePairing>; onRetry: () => void }) {
  const dev = pairing.deviceInfo;

  useEffect(() => {
    if (dev && pairing.step === 'discovering') {
      const t = setTimeout(() => pairing.connectUSB(), 500);
      return () => clearTimeout(t);
    }
  }, [dev, pairing.step]);

  return (
    <div className="glass rounded-2xl p-6 slide-in-up">
      <div className="flex items-center gap-3 mb-6">
        <div className="h-8 w-8 rounded-full bg-accent/10 flex items-center justify-center">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="oklch(0.78 0.11 70)" strokeWidth="1.5">
            <rect x="5" y="2" width="14" height="20" rx="3" />
            <line x1="12" y1="18" x2="12" y2="18.01" strokeWidth="2" strokeLinecap="round" />
          </svg>
        </div>
        <div>
          <p className="text-[13px] font-medium">USB Pairing</p>
          <p className="text-[10px] text-muted-foreground">Connect your Android device via USB cable</p>
        </div>
      </div>

      {!dev ? (
        <div className="text-center py-10">
          {pairing.loading ? (
            <div className="flex flex-col items-center gap-4">
              <ApaOrb size={60} state="thinking" />
              <p className="text-[13px] text-muted-foreground">Scanning for connected devices…</p>
              <div className="w-48 h-1 bg-[var(--color-border)] rounded-full overflow-hidden">
                <div className="h-full bg-accent progress-shimmer rounded-full" style={{ width: "60%" }} />
              </div>
            </div>
          ) : (
            <div className="flex flex-col items-center gap-4">
              <div className="w-16 h-16 rounded-2xl bg-surface border hairline flex items-center justify-center">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.2" className="text-muted-foreground">
                  <rect x="5" y="2" width="14" height="20" rx="3" />
                  <line x1="12" y1="18" x2="12" y2="18.01" strokeWidth="2" strokeLinecap="round" />
                </svg>
              </div>
              <div>
                <p className="text-[13px]">Connect your phone via USB</p>
                <p className="text-[11px] text-muted-foreground mt-1">Enable USB debugging in Developer Options</p>
              </div>
              <button
                onClick={onRetry}
                className="px-6 py-2.5 rounded-xl bg-accent text-accent-foreground text-[11px] uppercase tracking-[0.22em] font-medium hover:brightness-110 transition-all"
              >
                Scan for devices
              </button>
            </div>
          )}
        </div>
      ) : (
        <FoundDeviceCard
          device={dev}
          onConnect={() => pairing.connectUSB()}
          onVerify={() => {
            if (pairing.serial) {
              pairing.verifyDevice(pairing.serial);
            }
          }}
          onTrust={() => {
            if (pairing.deviceId) pairing.trustDevice(pairing.deviceId);
          }}
          step={pairing.step}
          loading={pairing.loading}
        />
      )}
    </div>
  );
}

/* ─── Found Device Card ─── */
function FoundDeviceCard({
  device, onConnect, onVerify, onTrust, step, loading,
}: {
  device: USBDeviceInfo;
  onConnect: () => void;
  onVerify: () => void;
  onTrust: () => void;
  step: string;
  loading: boolean;
}) {
  return (
    <div className="glass-subtle rounded-xl p-5 card-expand">
      <div className="flex items-center gap-4 mb-4">
        <div className="w-14 h-14 rounded-xl bg-surface border hairline flex items-center justify-center">
          <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.2">
            <rect x="5" y="2" width="14" height="20" rx="3" />
            <line x1="12" y1="18" x2="12" y2="18.01" strokeWidth="2" strokeLinecap="round" />
          </svg>
        </div>
        <div className="flex-1">
          <p className="text-[14px] font-medium">{device.device_name || device.model || 'Android Device'}</p>
          <p className="text-[11px] text-muted-foreground">{device.manufacturer} {device.model} · Android {device.android_version}</p>
        </div>
        <span className={`h-2.5 w-2.5 rounded-full ${step === 'ready' ? 'status-online' : loading ? 'status-pairing apa-pulse' : 'status-pairing'}`} />
      </div>

      <div className="grid grid-cols-3 gap-3 mb-4">
        {[
          ["Battery", device.battery_percentage > 0 ? `${device.battery_percentage}%` : device.charging ? 'Charging' : 'N/A'],
          ["Serial", (device.serial || '').slice(0, 8) + '…'],
          ["Screen", device.screen_width > 0 ? `${device.screen_width}×${device.screen_height}` : 'N/A'],
          ["USB Debug", device.usb_debugging ? 'Enabled' : 'Disabled'],
          ["Lock", device.lock_state || 'unknown'],
          ["ADB", device.adb_authorized ? 'Authorized' : 'Pending'],
        ].map(([label, value]) => (
          <div key={label} className="text-center">
            <p className="text-[9px] uppercase tracking-wider text-muted-foreground">{label}</p>
            <p className="mt-0.5 text-[11px] font-mono">{value}</p>
          </div>
        ))}
      </div>

      {/* Action buttons based on current step */}
      {step === 'discovering' && (
        <button
          onClick={onConnect}
          disabled={loading}
          className="w-full py-2.5 rounded-xl bg-accent text-accent-foreground text-[11px] uppercase tracking-[0.22em] font-medium hover:brightness-110 transition-all disabled:opacity-50"
        >
          {loading ? 'Connecting…' : 'Connect'}
        </button>
      )}

      {step === 'connecting' && (
        <button
          onClick={onVerify}
          disabled={loading}
          className="w-full py-2.5 rounded-xl bg-accent text-accent-foreground text-[11px] uppercase tracking-[0.22em] font-medium hover:brightness-110 transition-all disabled:opacity-50"
        >
          {loading ? 'Verifying…' : 'Verify Device'}
        </button>
      )}

      {step === 'verifying' && (
        <button
          onClick={onTrust}
          disabled={loading}
          className="w-full py-2.5 rounded-xl bg-accent text-accent-foreground text-[11px] uppercase tracking-[0.22em] font-medium hover:brightness-110 transition-all disabled:opacity-50"
        >
          {loading ? 'Processing…' : 'Trust Device'}
        </button>
      )}

      {(step === 'trusting' || step === 'permissions' || step === 'registering' || step === 'twin_creating') && (
        <div className="flex items-center justify-center gap-2 py-2 text-[11px] text-[color:var(--color-success)]">
          <svg width="14" height="14" viewBox="0 0 14 14" fill="none" className="animate-spin">
            <path d="M3 7L6 10L11 4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
          {step === 'trusting' ? 'Trusting…' : step === 'permissions' ? 'Configuring…' : step === 'registering' ? 'Registering…' : 'Creating twin…'}
        </div>
      )}
    </div>
  );
}

/* ─── Verify Panel ─── */
function VerifyPanel({ pairing }: { pairing: ReturnType<typeof useDevicePairing> }) {
  const [checks, setChecks] = useState([
    { label: "Device fingerprint", done: false },
    { label: "ADB authorization", done: false },
    { label: "Hardware identity", done: false },
  ]);

  useEffect(() => {
    checks.forEach((_, i) => {
      setTimeout(() => {
        setChecks(prev => prev.map((c, j) => j <= i ? { ...c, done: true } : c));
      }, (i + 1) * 800);
    });
  }, []);

  useEffect(() => {
    const serial = pairing.serial;
    if (checks.every(c => c.done) && serial) {
      const t = setTimeout(() => {
        if (pairing.deviceId) pairing.trustDevice(pairing.deviceId);
      }, 500);
      return () => clearTimeout(t);
    }
  }, [checks, pairing.serial, pairing.deviceId]);

  return (
    <div className="glass rounded-2xl p-6 slide-in-up">
      <div className="flex items-center gap-3 mb-6">
        <div className="h-8 w-8 rounded-full bg-accent/10 flex items-center justify-center">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="oklch(0.78 0.11 70)" strokeWidth="1.5">
            <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
          </svg>
        </div>
        <div>
          <p className="text-[13px] font-medium">Device Verification</p>
          <p className="text-[10px] text-muted-foreground">Confirming device identity…</p>
        </div>
      </div>
      <div className="space-y-3">
        {checks.map((item) => (
          <div key={item.label} className="flex items-center justify-between px-4 py-3 rounded-xl bg-surface/40">
            <span className="text-[12px]">{item.label}</span>
            <span className={`text-[10px] font-mono uppercase tracking-wider ${item.done ? "text-[color:var(--color-success)]" : "text-accent apa-pulse"}`}>
              {item.done ? 'confirmed' : 'verifying…'}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

/* ─── Trust Panel ─── */
function TrustPanel({ pairing, deviceName }: { pairing: ReturnType<typeof useDevicePairing>; deviceName: string }) {
  return (
    <div className="glass rounded-2xl p-6 slide-in-up">
      <div className="flex items-center gap-3 mb-6">
        <div className="h-8 w-8 rounded-full bg-accent/10 flex items-center justify-center">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="oklch(0.78 0.11 70)" strokeWidth="1.5">
            <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
            <path d="M9 12l2 2 4-4" />
          </svg>
        </div>
        <div>
          <p className="text-[13px] font-medium">Trust Device</p>
          <p className="text-[10px] text-muted-foreground">Authorize this device for AI control</p>
        </div>
      </div>

      <div className="glass-subtle rounded-xl p-5 mb-5">
        <div className="flex items-center gap-3 mb-3">
          <div className="w-10 h-10 rounded-xl bg-surface border hairline flex items-center justify-center">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.2">
              <rect x="5" y="2" width="14" height="20" rx="3" />
              <line x1="12" y1="18" x2="12" y2="18.01" strokeWidth="2" strokeLinecap="round" />
            </svg>
          </div>
          <div>
            <p className="text-[13px] font-medium">{deviceName}</p>
          </div>
        </div>
        <p className="text-[11px] text-muted-foreground leading-relaxed">
          Trusting this device allows APA-OS to capture screenshots, navigate apps, and execute outcomes on your behalf.
          You can revoke trust at any time from Settings → Devices.
        </p>
      </div>

      <button
        onClick={async () => {
          if (!pairing.deviceId) return;
          await pairing.trustDevice(pairing.deviceId);
          if (pairing.deviceId) {
            await pairing.syncPermissions(pairing.deviceId);
          }
        }}
        disabled={pairing.loading}
        className="w-full py-3 rounded-xl bg-accent text-accent-foreground text-[11px] uppercase tracking-[0.22em] font-medium hover:brightness-110 transition-all disabled:opacity-50"
      >
        {pairing.loading ? 'Processing…' : 'Trust this device'}
      </button>
    </div>
  );
}

/* ─── Permissions Panel ─── */
function PermissionsPanel({
  onGrant, granted, onContinue, loading,
}: {
  onGrant: () => void; granted: boolean; onContinue: () => void; loading: boolean;
}) {
  return (
    <div className="glass rounded-2xl p-6 slide-in-up">
      <div className="flex items-center gap-3 mb-6">
        <div className="h-8 w-8 rounded-full bg-accent/10 flex items-center justify-center">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="oklch(0.78 0.11 70)" strokeWidth="1.5">
            <rect x="3" y="11" width="18" height="11" rx="2" />
            <path d="M7 11V7a5 5 0 0110 0v4" />
          </svg>
        </div>
        <div>
          <p className="text-[13px] font-medium">Permission Review</p>
          <p className="text-[10px] text-muted-foreground">Granting required capabilities via backend</p>
        </div>
      </div>

      <div className="space-y-3">
        {[
          { id: 'screen_capture', label: 'Screen Capture', detail: 'Take and analyze screenshots', icon: '◎' },
          { id: 'navigation', label: 'Navigation', detail: 'Swipe, tap, and scroll on device', icon: '↻' },
          { id: 'notifications', label: 'Notifications', detail: 'Read and manage notifications', icon: '◈' },
          { id: 'files', label: 'File Access', detail: 'Read and organize files', icon: '◇' },
          { id: 'accessibility', label: 'Accessibility', detail: 'UI control and state detection', icon: '⬡' },
          { id: 'overlay', label: 'Overlay', detail: 'Display controls over other apps', icon: '○' },
        ].map((p) => (
          <div key={p.id} className="flex items-center justify-between px-4 py-3.5 rounded-xl bg-accent/10 border border-accent/30">
            <div className="flex items-center gap-3">
              <span className="text-accent text-[16px] w-6 text-center">{p.icon}</span>
              <div className="text-left">
                <p className="text-[12px] font-medium">{p.label}</p>
                <p className="text-[10px] text-muted-foreground">{p.detail}</p>
              </div>
            </div>
            <div className="w-5 h-5 rounded-md bg-accent border-accent flex items-center justify-center">
              <svg width="10" height="8" viewBox="0 0 10 8" fill="none">
                <path d="M1 4L3.5 6.5L9 1" stroke="oklch(0.14 0 0)" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
            </div>
          </div>
        ))}
      </div>

      {!granted ? (
        <button
          onClick={onGrant}
          className="mt-5 w-full py-3 rounded-xl bg-accent text-accent-foreground text-[11px] uppercase tracking-[0.22em] font-medium hover:brightness-110 transition-all"
        >
          Grant all permissions
        </button>
      ) : (
        <button
          onClick={onContinue}
          disabled={loading}
          className="mt-5 w-full py-3 rounded-xl bg-accent text-accent-foreground text-[11px] uppercase tracking-[0.22em] font-medium transition-all duration-300 disabled:opacity-50 hover:brightness-110"
        >
          {loading ? 'Registering & creating twin…' : 'Continue to ready'}
        </button>
      )}
    </div>
  );
}

/* ─── Ready Panel ─── */
function ReadyPanel({
  deviceName, capabilities, readinessScore,
}: {
  deviceName: string; capabilities: string[]; readinessScore: number;
}) {
  const navigate = useNavigate();
  return (
    <div className="glass rounded-2xl p-8 text-center slide-in-up">
      <div className="mx-auto mb-6">
        <ApaOrb size={70} state="success" />
      </div>
      <h2 className="font-display text-[24px] tracking-tight">Device Connected</h2>
      <p className="mt-2 text-[13px] text-muted-foreground">
        {deviceName} is paired, verified, and ready for AI control.
      </p>
      {readinessScore > 0 && (
        <p className="mt-1 text-[11px] text-accent font-mono">AI Readiness: {readinessScore.toFixed(0)}%</p>
      )}
      <div className="mt-6 flex flex-wrap justify-center gap-2">
        {capabilities.map((c) => (
          <span key={c} className="px-3 py-1.5 rounded-full bg-accent/10 text-[10px] text-accent uppercase tracking-wider">
            {c}
          </span>
        ))}
      </div>
      <button
        onClick={() => navigate({ to: '/dashboard' })}
        className="mt-8 inline-flex items-center gap-2 px-8 py-3.5 rounded-xl bg-accent text-accent-foreground text-[12px] uppercase tracking-[0.22em] font-medium hover:brightness-110 hover:shadow-[0_0_30px_-4px_oklch(0.78_0.11_70/0.4)] transition-all btn-pulse"
      >
        Go to Dashboard →
      </button>
    </div>
  );
}

/* ─── Live Device Card ─── */
function LiveDeviceCard({
  deviceName, model, manufacturer, android, battery, charging, serial,
  screen, foreground, lockState, online, connected, scanning,
}: {
  deviceName: string; model: string; manufacturer: string; android: string;
  battery: number; charging: boolean; serial: string; screen: string;
  foreground: string; lockState: string; online: boolean; connected: boolean; scanning: boolean;
}) {
  return (
    <div className="glass rounded-2xl p-5 card-expand">
      <p className="text-[9px] uppercase tracking-[0.22em] text-accent mb-3">Live Device</p>
      <div className="flex items-center gap-3 mb-4">
        <div className="w-12 h-12 rounded-xl bg-surface border hairline flex items-center justify-center">
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.2">
            <rect x="5" y="2" width="14" height="20" rx="3" />
            <line x1="12" y1="18" x2="12" y2="18.01" strokeWidth="2" strokeLinecap="round" />
          </svg>
        </div>
        <div className="flex-1 min-w-0">
          <p className="text-[13px] font-medium truncate">{deviceName}</p>
          <p className="text-[10px] text-muted-foreground">{manufacturer} {model}</p>
        </div>
        <span className={`h-2 w-2 rounded-full ${connected ? 'status-online' : scanning ? 'status-pairing apa-pulse' : online ? 'status-pairing' : 'status-offline'}`} />
      </div>

      <div className="space-y-2">
        {[
          ["Android", android],
          ["Battery", charging ? `${battery}% ⚡` : `${battery}%`],
          ["Screen", screen],
          ["Foreground", foreground || '—'],
          ["Lock", lockState],
        ].map(([label, value]) => (
          <div key={label} className="flex items-center justify-between py-1.5 border-b border-[var(--color-border)] last:border-0">
            <span className="text-[10px] text-muted-foreground">{label}</span>
            <span className="text-[11px] font-mono">{value}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

/* ─── Connection Status Panel ─── */
function ConnectionStatusPanel({
  method, connected, verified, trusted, aiReady,
}: {
  method: PairingMethod | null; connected: boolean; verified: boolean; trusted: boolean; aiReady: boolean;
}) {
  return (
    <div className="glass rounded-2xl p-5">
      <p className="text-[9px] uppercase tracking-[0.22em] text-muted-foreground mb-3">Connection Status</p>
      <div className="space-y-3">
        {[
          { label: "USB Bridge", active: method === "usb" && (connected || verified || trusted || aiReady) },
          { label: "ADB Channel", active: connected || verified || trusted || aiReady },
          { label: "Device Verified", active: verified || trusted || aiReady },
          { label: "Trusted", active: trusted || aiReady },
          { label: "AI Agent Link", active: aiReady },
        ].map((s) => (
          <div key={s.label} className="flex items-center justify-between">
            <span className="flex items-center gap-2 text-[11px]">
              <span className={`h-1.5 w-1.5 rounded-full ${s.active ? "bg-[color:var(--color-success)]" : "bg-muted-foreground/25"}`} />
              {s.label}
            </span>
            <span className={`text-[9px] font-mono uppercase tracking-wider ${s.active ? "text-[color:var(--color-success)]" : "text-muted-foreground/50"}`}>
              {s.active ? "active" : "pending"}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
