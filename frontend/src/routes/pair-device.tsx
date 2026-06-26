import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { useState, useEffect, useRef } from "react";
import { ApaOrb } from "@/components/apa/ApaOrb";

export const Route = createFileRoute("/pair-device")({
  head: () => ({ meta: [{ title: "Pair Device — APA-OS" }] }),
  component: PairDevicePage,
});

type PairingMethod = "usb" | "wireless" | "qr";
type PairingStep = "discover" | "connect" | "verify" | "trust" | "permissions" | "ready";

const STEPS: { key: PairingStep; label: string; detail: string }[] = [
  { key: "discover", label: "Discover", detail: "Find your device" },
  { key: "connect", label: "Connect", detail: "Establish link" },
  { key: "verify", label: "Verify", detail: "Confirm identity" },
  { key: "trust", label: "Trust", detail: "Authorize access" },
  { key: "permissions", label: "Permissions", detail: "Grant capabilities" },
  { key: "ready", label: "Ready", detail: "AI connected" },
];

const MOCK_DEVICE = {
  name: "Pixel 8 Pro",
  model: "Google Pixel 8 Pro",
  android: "15",
  battery: 78,
  ip: "192.168.1.42",
  serial: "RXCN30XXXXX",
  brand: "Google",
  screen: "2400 × 1080",
  foregroundApp: "Chrome",
  lockState: "Unlocked",
  trustLevel: "Trusted",
  capabilities: ["Screenshot", "Navigation", "OCR", "App Control", "Notifications", "File Access"],
};

const PERMISSIONS = [
  { id: "screenshot", label: "Screen Capture", detail: "Take and analyze screenshots", icon: "◎" },
  { id: "navigation", label: "Navigation", detail: "Swipe, tap, and scroll on device", icon: "↻" },
  { id: "notifications", label: "Notifications", detail: "Read and manage notifications", icon: "◈" },
  { id: "files", label: "File Access", detail: "Read and organize files", icon: "◇" },
  { id: "apps", label: "App Control", detail: "Open and interact with apps", icon: "⬡" },
  { id: "camera", label: "Camera", detail: "Access camera for QR and visual input", icon: "○" },
];

function PairDevicePage() {
  const navigate = useNavigate();
  const [method, setMethod] = useState<PairingMethod | null>(null);
  const [step, setStep] = useState<PairingStep>("discover");
  const [stepIdx, setStepIdx] = useState(0);
  const [pairCode, setPairCode] = useState(() => Math.random().toString(36).slice(2, 8).toUpperCase());
  const [wirelessIp, setWirelessIp] = useState("");
  const [wirelessPort, setWirelessPort] = useState("5555");
  const [wirelessCode, setWirelessCode] = useState("");
  const [scanning, setScanning] = useState(false);
  const [deviceFound, setDeviceFound] = useState(false);
  const [connected, setConnected] = useState(false);
  const [verified, setVerified] = useState(false);
  const [trusted, setTrusted] = useState(false);
  const [permissions, setPermissions] = useState<Record<string, boolean>>({});
  const [mounted, setMounted] = useState(false);

  useEffect(() => { setMounted(true); }, []);

  // Simulate device discovery
  useEffect(() => {
    if (!scanning) return;
    const t = setTimeout(() => {
      setScanning(false);
      setDeviceFound(true);
    }, 2000);
    return () => clearTimeout(t);
  }, [scanning]);

  // Auto-advance steps
  useEffect(() => {
    if (deviceFound && step === "discover") {
      const t = setTimeout(() => advanceStep(), 800);
      return () => clearTimeout(t);
    }
    if (connected && step === "connect") {
      const t = setTimeout(() => advanceStep(), 800);
      return () => clearTimeout(t);
    }
    if (verified && step === "verify") {
      const t = setTimeout(() => advanceStep(), 800);
      return () => clearTimeout(t);
    }
    if (trusted && step === "trust") {
      const t = setTimeout(() => advanceStep(), 800);
      return () => clearTimeout(t);
    }
  }, [deviceFound, connected, verified, trusted, step]);

  function advanceStep() {
    setStepIdx((i) => Math.min(i + 1, STEPS.length - 1));
    setStep(STEPS[Math.min(stepIdx + 1, STEPS.length - 1)].key);
  }

  function startScan() {
    setScanning(true);
    setDeviceFound(false);
  }

  function connectDevice() {
    setConnected(true);
  }

  function verifyDevice() {
    setVerified(true);
  }

  function trustDevice() {
    setTrusted(true);
  }

  function togglePermission(id: string) {
    setPermissions((p) => ({ ...p, [id]: !p[id] }));
  }

  const allPermissionsGranted = PERMISSIONS.every((p) => permissions[p.id]);

  return (
    <div className="min-h-screen bg-background text-foreground grain">
      {/* Header */}
      <header className="border-b hairline px-6 lg:px-10 py-6">
        <div className="max-w-[1400px] mx-auto flex items-center justify-between">
          <Link to="/" className="flex items-center gap-2">
            <ApaOrb size={28} state="idle" />
            <span className="font-display text-[18px] tracking-tight">apa<span className="text-accent">·</span>os</span>
          </Link>
          <div className="flex items-center gap-3">
            <span className="text-[10px] uppercase tracking-[0.18em] text-muted-foreground">
              Onboarding · Step 2 of 5
            </span>
            <Link
              to="/setup-check"
              className="text-[11px] text-muted-foreground hover:text-foreground transition-colors uppercase tracking-[0.18em]"
            >
              Skip →
            </Link>
          </div>
        </div>
      </header>

      <div className="max-w-[1400px] mx-auto px-6 lg:px-10 py-8">
        {/* Page title */}
        <div className={`mb-8 transition-all duration-700 ${mounted ? "opacity-100 translate-y-0" : "opacity-0 translate-y-4"}`}>
          <p className="text-[10px] uppercase tracking-[0.28em] text-accent mb-3">Device Pairing Center</p>
          <h1 className="font-display text-[36px] lg:text-[44px] tracking-tight leading-[1.02]">
            Connect your phone.
          </h1>
          <p className="mt-3 text-[14px] text-muted-foreground max-w-[500px] leading-relaxed">
            Install the APA-OS Agent on Android. Pair via USB, wireless, or QR. Your phone becomes part of your operating system.
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

        {/* Main content */}
        <div className="grid lg:grid-cols-[1fr_380px] gap-6">
          {/* Left: Main pairing area */}
          <div className={`transition-all duration-500 ${mounted ? "opacity-100 translate-y-0" : "opacity-0 translate-y-4"}`} style={{ transitionDelay: "300ms" }}>
            {/* Pairing method selection */}
            {!method && step === "discover" && (
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
                      onClick={() => { setMethod(m.id); startScan(); }}
                      className="glass rounded-2xl p-6 text-left hover-lift hover-glow transition-all duration-300 group"
                    >
                      <div className="text-accent mb-4 group-hover:scale-110 transition-transform duration-300">{m.icon}</div>
                      <p className="text-[14px] font-medium">{m.title}</p>
                      <p className="mt-1 text-[11px] text-muted-foreground">{m.detail}</p>
                    </button>
                  ))}
                </div>
              </div>
            )}

            {/* USB Pairing */}
            {method === "usb" && step !== "ready" && (
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

                {!deviceFound ? (
                  <div className="text-center py-10">
                    {scanning ? (
                      <div className="flex flex-col items-center gap-4">
                        <div className="relative">
                          <ApaOrb size={60} state="thinking" />
                        </div>
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
                          onClick={startScan}
                          className="px-6 py-2.5 rounded-xl bg-accent text-accent-foreground text-[11px] uppercase tracking-[0.22em] font-medium hover:brightness-110 transition-all"
                        >
                          Scan for devices
                        </button>
                      </div>
                    )}
                  </div>
                ) : (
                  /* Device found - show device card */
                  <DeviceCard device={MOCK_DEVICE} onConnect={connectDevice} connected={connected} />
                )}
              </div>
            )}

            {/* Wireless ADB */}
            {method === "wireless" && step !== "ready" && (
              <div className="glass rounded-2xl p-6 slide-in-up">
                <div className="flex items-center gap-3 mb-6">
                  <div className="h-8 w-8 rounded-full bg-accent/10 flex items-center justify-center">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="oklch(0.78 0.11 70)" strokeWidth="1.5">
                      <path d="M5 12.55a11 11 0 0114.08 0" />
                      <path d="M8.53 16.11a6 6 0 016.95 0" />
                      <circle cx="12" cy="20" r="1" fill="oklch(0.78 0.11 70)" />
                    </svg>
                  </div>
                  <div>
                    <p className="text-[13px] font-medium">Wireless ADB Pairing</p>
                    <p className="text-[10px] text-muted-foreground">Enter your device IP and pairing code</p>
                  </div>
                </div>

                <div className="space-y-4">
                  <div className="grid grid-cols-[1fr_100px] gap-3">
                    <label className="block">
                      <span className="text-[9px] uppercase tracking-[0.22em] text-muted-foreground">Device IP</span>
                      <input
                        value={wirelessIp}
                        onChange={(e) => setWirelessIp(e.target.value)}
                        placeholder="192.168.1.42"
                        className="mt-1.5 w-full bg-transparent border hairline rounded-xl px-4 py-2.5 text-[13px] font-mono outline-none focus:border-accent input-glow transition-all placeholder:text-muted-foreground/30"
                      />
                    </label>
                    <label className="block">
                      <span className="text-[9px] uppercase tracking-[0.22em] text-muted-foreground">Port</span>
                      <input
                        value={wirelessPort}
                        onChange={(e) => setWirelessPort(e.target.value)}
                        placeholder="5555"
                        className="mt-1.5 w-full bg-transparent border hairline rounded-xl px-4 py-2.5 text-[13px] font-mono outline-none focus:border-accent input-glow transition-all placeholder:text-muted-foreground/30"
                      />
                    </label>
                  </div>

                  <label className="block">
                    <span className="text-[9px] uppercase tracking-[0.22em] text-muted-foreground">Pairing code (from device)</span>
                    <input
                      value={wirelessCode}
                      onChange={(e) => setWirelessCode(e.target.value.toUpperCase())}
                      placeholder="XXXXXX"
                      maxLength={6}
                      className="mt-1.5 w-full bg-transparent border hairline rounded-xl px-4 py-3 text-[18px] font-mono tracking-[0.3em] text-center outline-none focus:border-accent input-glow transition-all placeholder:text-muted-foreground/30"
                    />
                  </label>

                  <button
                    onClick={() => { setDeviceFound(true); setConnected(true); }}
                    disabled={wirelessIp.length < 7 || wirelessCode.length < 4}
                    className="w-full py-3 rounded-xl bg-accent text-accent-foreground text-[11px] uppercase tracking-[0.22em] font-medium transition-all duration-300 disabled:opacity-40 disabled:cursor-not-allowed hover:brightness-110"
                  >
                    Connect
                  </button>

                  <p className="text-[10px] text-muted-foreground/60 text-center">
                    Enable wireless debugging in Developer Options → Pair device with pairing code
                  </p>
                </div>
              </div>
            )}

            {/* QR Pairing */}
            {method === "qr" && step !== "ready" && (
              <div className="glass rounded-2xl p-6 slide-in-up">
                <div className="flex items-center gap-3 mb-6">
                  <div className="h-8 w-8 rounded-full bg-accent/10 flex items-center justify-center">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="oklch(0.78 0.11 70)" strokeWidth="1.5">
                      <rect x="3" y="3" width="7" height="7" rx="1" />
                      <rect x="14" y="3" width="7" height="7" rx="1" />
                      <rect x="3" y="14" width="7" height="7" rx="1" />
                    </svg>
                  </div>
                  <div>
                    <p className="text-[13px] font-medium">QR Code Pairing</p>
                    <p className="text-[10px] text-muted-foreground">Scan with APA-OS Agent on your phone</p>
                  </div>
                </div>

                <div className="flex flex-col items-center gap-5">
                  {/* QR Code */}
                  <div className="aspect-square w-[240px] border-2 hairline-strong rounded-2xl p-4 bg-white/5 flex items-center justify-center">
                    <QrCode code={pairCode} />
                  </div>
                  <p className="font-mono text-[16px] tracking-[0.4em] text-accent">{pairCode}</p>
                  <p className="text-[10px] text-muted-foreground">Pair code · expires in 5 minutes</p>

                  {/* Scan instructions */}
                  <div className="w-full space-y-2">
                    {[
                      "Open APA-OS Agent on your phone",
                      "Tap 'Pair with Computer'",
                      "Scan this QR code",
                    ].map((text, i) => (
                      <div key={i} className="flex items-center gap-3 px-4 py-2.5 rounded-xl bg-surface/40">
                        <span className="h-5 w-5 rounded-full bg-accent/10 flex items-center justify-center shrink-0 text-[10px] font-mono text-accent">
                          {i + 1}
                        </span>
                        <span className="text-[12px] text-muted-foreground">{text}</span>
                      </div>
                    ))}
                  </div>

                  <button
                    onClick={() => { setDeviceFound(true); setConnected(true); }}
                    className="px-6 py-2.5 rounded-xl bg-accent text-accent-foreground text-[11px] uppercase tracking-[0.22em] font-medium hover:brightness-110 transition-all"
                  >
                    Simulate scan
                  </button>
                </div>
              </div>
            )}

            {/* Verify / Trust / Permissions steps */}
            {step === "verify" && deviceFound && (
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
                  {[
                    { label: "Device fingerprint", status: verified ? "matched" : "verifying…", done: verified },
                    { label: "ADB authorization", status: verified ? "confirmed" : "checking…", done: verified },
                    { label: "Secure channel", status: verified ? "established" : "negotiating…", done: verified },
                  ].map((item, i) => (
                    <div key={i} className="flex items-center justify-between px-4 py-3 rounded-xl bg-surface/40">
                      <span className="text-[12px]">{item.label}</span>
                      <span className={`text-[10px] font-mono uppercase tracking-wider ${item.done ? "text-[color:var(--color-success)]" : "text-accent apa-pulse"}`}>
                        {item.status}
                      </span>
                    </div>
                  ))}
                </div>

                {!verified && (
                  <button
                    onClick={verifyDevice}
                    className="mt-5 w-full py-3 rounded-xl bg-accent text-accent-foreground text-[11px] uppercase tracking-[0.22em] font-medium hover:brightness-110 transition-all"
                  >
                    Complete verification
                  </button>
                )}
              </div>
            )}

            {step === "trust" && (
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
                      <p className="text-[13px] font-medium">{MOCK_DEVICE.name}</p>
                      <p className="text-[10px] text-muted-foreground">{MOCK_DEVICE.model} · Android {MOCK_DEVICE.android}</p>
                    </div>
                  </div>
                  <p className="text-[11px] text-muted-foreground leading-relaxed">
                    Trusting this device allows APA-OS to capture screenshots, navigate apps, and execute outcomes on your behalf.
                    You can revoke trust at any time from Settings → Devices.
                  </p>
                </div>

                <button
                  onClick={trustDevice}
                  className="w-full py-3 rounded-xl bg-accent text-accent-foreground text-[11px] uppercase tracking-[0.22em] font-medium hover:brightness-110 transition-all"
                >
                  Trust this device
                </button>
              </div>
            )}

            {step === "permissions" && (
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
                    <p className="text-[10px] text-muted-foreground">Choose what APA-OS can access</p>
                  </div>
                </div>

                <div className="space-y-3">
                  {PERMISSIONS.map((p) => (
                    <button
                      key={p.id}
                      onClick={() => togglePermission(p.id)}
                      className={`w-full flex items-center justify-between px-4 py-3.5 rounded-xl transition-all duration-200 ${
                        permissions[p.id]
                          ? "bg-accent/10 border border-accent/30"
                          : "bg-surface/40 border border-transparent hover:border-[var(--color-border)]"
                      }`}
                    >
                      <div className="flex items-center gap-3">
                        <span className="text-accent text-[16px] w-6 text-center">{p.icon}</span>
                        <div className="text-left">
                          <p className="text-[12px] font-medium">{p.label}</p>
                          <p className="text-[10px] text-muted-foreground">{p.detail}</p>
                        </div>
                      </div>
                      <div className={`w-5 h-5 rounded-md border flex items-center justify-center transition-all ${
                        permissions[p.id]
                          ? "bg-accent border-accent"
                          : "border-muted-foreground/30"
                      }`}>
                        {permissions[p.id] && (
                          <svg width="10" height="8" viewBox="0 0 10 8" fill="none">
                            <path d="M1 4L3.5 6.5L9 1" stroke="oklch(0.14 0 0)" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
                          </svg>
                        )}
                      </div>
                    </button>
                  ))}
                </div>

                <button
                  onClick={() => { setStepIdx(STEPS.length - 1); setStep("ready"); }}
                  disabled={!allPermissionsGranted}
                  className="mt-5 w-full py-3 rounded-xl bg-accent text-accent-foreground text-[11px] uppercase tracking-[0.22em] font-medium transition-all duration-300 disabled:opacity-40 disabled:cursor-not-allowed hover:brightness-110"
                >
                  {allPermissionsGranted ? "Continue" : `Grant all permissions (${Object.values(permissions).filter(Boolean).length}/${PERMISSIONS.length})`}
                </button>
              </div>
            )}

            {/* Ready state */}
            {step === "ready" && (
              <div className="glass rounded-2xl p-8 text-center slide-in-up">
                <div className="mx-auto mb-6">
                  <ApaOrb size={70} state="success" />
                </div>
                <h2 className="font-display text-[24px] tracking-tight">Device Connected</h2>
                <p className="mt-2 text-[13px] text-muted-foreground">
                  {MOCK_DEVICE.name} is paired, verified, and ready for AI control.
                </p>
                <div className="mt-6 flex flex-wrap justify-center gap-2">
                  {MOCK_DEVICE.capabilities.map((c) => (
                    <span key={c} className="px-3 py-1.5 rounded-full bg-accent/10 text-[10px] text-accent uppercase tracking-wider">
                      {c}
                    </span>
                  ))}
                </div>
                <Link
                  to="/setup-check"
                  className="mt-8 inline-flex items-center gap-2 px-8 py-3.5 rounded-xl bg-accent text-accent-foreground text-[12px] uppercase tracking-[0.22em] font-medium hover:brightness-110 hover:shadow-[0_0_30px_-4px_oklch(0.78_0.11_70/0.4)] transition-all btn-pulse"
                >
                  Continue to AI Check →
                </Link>
              </div>
            )}
          </div>

          {/* Right: Device Preview + Status */}
          <aside className={`space-y-4 transition-all duration-500 ${mounted ? "opacity-100 translate-y-0" : "opacity-0 translate-y-4"}`} style={{ transitionDelay: "400ms" }}>
            {/* Live Device Card */}
            {(deviceFound || connected) && (
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
                    <p className="text-[13px] font-medium truncate">{MOCK_DEVICE.name}</p>
                    <p className="text-[10px] text-muted-foreground">{MOCK_DEVICE.model}</p>
                  </div>
                  <span className={`h-2 w-2 rounded-full ${connected ? "status-online" : scanning ? "status-pairing apa-pulse" : "status-offline"}`} />
                </div>

                <div className="space-y-2">
                  {[
                    ["Android", MOCK_DEVICE.android],
                    ["Battery", `${MOCK_DEVICE.battery}%`],
                    ["Screen", MOCK_DEVICE.screen],
                    ["Foreground", MOCK_DEVICE.foregroundApp],
                    ["Lock", MOCK_DEVICE.lockState],
                    ["Trust", MOCK_DEVICE.trustLevel],
                  ].map(([label, value]) => (
                    <div key={label} className="flex items-center justify-between py-1.5 border-b border-[var(--color-border)] last:border-0">
                      <span className="text-[10px] text-muted-foreground">{label}</span>
                      <span className="text-[11px] font-mono">{value}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Connection Status */}
            <div className="glass rounded-2xl p-5">
              <p className="text-[9px] uppercase tracking-[0.22em] text-muted-foreground mb-3">Connection Status</p>
              <div className="space-y-3">
                {[
                  { label: "USB Bridge", active: method === "usb" && connected },
                  { label: "ADB Channel", active: connected },
                  { label: "Secure Tunnel", active: verified },
                  { label: "AI Agent Link", active: step === "ready" },
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

            {/* What you'll grant */}
            <div className="glass rounded-2xl p-5">
              <p className="text-[9px] uppercase tracking-[0.22em] text-muted-foreground mb-3">Capabilities</p>
              <div className="space-y-2">
                {MOCK_DEVICE.capabilities.map((c) => (
                  <div key={c} className="flex items-center gap-2 text-[11px] text-muted-foreground">
                    <span className="h-1 w-1 rounded-full bg-accent/50" />
                    {c}
                  </div>
                ))}
              </div>
            </div>

            {/* Help */}
            <div className="glass-subtle rounded-2xl p-5">
              <p className="text-[9px] uppercase tracking-[0.22em] text-muted-foreground mb-2">Need help?</p>
              <p className="text-[11px] text-muted-foreground leading-relaxed">
                Ensure USB debugging is enabled in Developer Options. For wireless pairing, both devices must be on the same network.
              </p>
              <a href="#" className="mt-2 inline-block text-[10px] text-accent hover:text-accent/80 transition-colors">
                View setup guide →
              </a>
            </div>
          </aside>
        </div>
      </div>
    </div>
  );
}

/* ─── Device Card Component ─── */
function DeviceCard({ device, onConnect, connected }: { device: typeof MOCK_DEVICE; onConnect: () => void; connected: boolean }) {
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
          <p className="text-[14px] font-medium">{device.name}</p>
          <p className="text-[11px] text-muted-foreground">{device.model} · Android {device.android}</p>
        </div>
        <span className={`h-2.5 w-2.5 rounded-full ${connected ? "status-online" : "status-pairing apa-pulse"}`} />
      </div>

      <div className="grid grid-cols-3 gap-3 mb-4">
        {[
          ["Battery", `${device.battery}%`],
          ["Serial", device.serial.slice(0, 8) + "…"],
          ["Screen", device.screen],
        ].map(([label, value]) => (
          <div key={label} className="text-center">
            <p className="text-[9px] uppercase tracking-wider text-muted-foreground">{label}</p>
            <p className="mt-0.5 text-[11px] font-mono">{value}</p>
          </div>
        ))}
      </div>

      {!connected ? (
        <button
          onClick={onConnect}
          className="w-full py-2.5 rounded-xl bg-accent text-accent-foreground text-[11px] uppercase tracking-[0.22em] font-medium hover:brightness-110 transition-all"
        >
          Connect
        </button>
      ) : (
        <div className="flex items-center justify-center gap-2 py-2 text-[11px] text-[color:var(--color-success)]">
          <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
            <path d="M3 7L6 10L11 4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
          Connected
        </div>
      )}
    </div>
  );
}

/* ─── QR Code Generator ─── */
function QrCode({ code }: { code: string }) {
  const cells = 21;
  const seed = code.split("").reduce((a, c) => a + c.charCodeAt(0), 0);
  return (
    <svg viewBox={`0 0 ${cells} ${cells}`} className="w-full h-full text-gray-900">
      {Array.from({ length: cells * cells }).map((_, i) => {
        const x = i % cells;
        const y = Math.floor(i / cells);
        const corner = (x < 7 && y < 7) || (x >= cells - 7 && y < 7) || (x < 7 && y >= cells - 7);
        const on = corner
          ? (x === 0 || x === 6 || y === 0 || y === 6) || (x >= 2 && x <= 4 && y >= 2 && y <= 4)
          : (seed * (x + 1) * (y + 1)) % 3 === 0;
        return on ? <rect key={i} x={x} y={y} width={1} height={1} fill="currentColor" /> : null;
      })}
    </svg>
  );
}
