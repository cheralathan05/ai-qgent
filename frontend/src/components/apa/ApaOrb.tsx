import { useEffect, useRef, useMemo } from "react";

type OrbState = "idle" | "listening" | "thinking" | "speaking" | "success" | "error";

interface ApaOrbProps {
  size?: number;
  state?: OrbState;
  className?: string;
  interactive?: boolean;
  onClick?: () => void;
}

const STATE_COLORS: Record<OrbState, string> = {
  idle: "oklch(0.78 0.11 70)",
  listening: "oklch(0.78 0.11 70)",
  thinking: "oklch(0.72 0.12 250)",
  speaking: "oklch(0.78 0.11 70)",
  success: "oklch(0.72 0.12 150)",
  error: "oklch(0.62 0.18 25)",
};

const STATE_GLOWS: Record<OrbState, string> = {
  idle: "0 0 40px oklch(0.78 0.11 70 / 0.3), 0 0 80px oklch(0.78 0.11 70 / 0.15)",
  listening: "0 0 50px oklch(0.78 0.11 70 / 0.4), 0 0 100px oklch(0.78 0.11 70 / 0.2)",
  thinking: "0 0 50px oklch(0.72 0.12 250 / 0.4), 0 0 100px oklch(0.72 0.12 250 / 0.2)",
  speaking: "0 0 60px oklch(0.78 0.11 70 / 0.5), 0 0 120px oklch(0.78 0.11 70 / 0.25)",
  success: "0 0 50px oklch(0.72 0.12 150 / 0.4), 0 0 100px oklch(0.72 0.12 150 / 0.2)",
  error: "0 0 50px oklch(0.62 0.18 25 / 0.4), 0 0 100px oklch(0.62 0.18 25 / 0.2)",
};

export function ApaOrb({ size = 120, state = "idle", className = "", interactive = false, onClick }: ApaOrbProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const animRef = useRef<number>(0);
  const timeRef = useRef(0);

  const color = STATE_COLORS[state];
  const glow = STATE_GLOWS[state];

  const particles = useMemo(() => {
    return Array.from({ length: 40 }, () => ({
      angle: Math.random() * Math.PI * 2,
      radius: 0.3 + Math.random() * 0.6,
      speed: 0.002 + Math.random() * 0.004,
      size: 0.5 + Math.random() * 1.5,
      opacity: 0.2 + Math.random() * 0.5,
      drift: (Math.random() - 0.5) * 0.01,
    }));
  }, []);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const dpr = window.devicePixelRatio || 1;
    const dim = size * 1.8;
    canvas.width = dim * dpr;
    canvas.height = dim * dpr;
    canvas.style.width = `${dim}px`;
    canvas.style.height = `${dim}px`;
    ctx.scale(dpr, dpr);

    const cx = dim / 2;
    const cy = dim / 2;
    const baseRadius = size * 0.35;

    function draw() {
      timeRef.current += 0.016;
      const t = timeRef.current;
      ctx!.clearRect(0, 0, dim, dim);

      // Outer glow
      const breathe = 1 + Math.sin(t * 0.8) * 0.04;
      const glowRadius = baseRadius * 2.2 * breathe;
      const grd = ctx!.createRadialGradient(cx, cy, baseRadius * 0.3, cx, cy, glowRadius);
      grd.addColorStop(0, color.replace(")", " / 0.15)").replace("oklch(", "oklch("));
      grd.addColorStop(0.5, color.replace(")", " / 0.05)").replace("oklch(", "oklch("));
      grd.addColorStop(1, "transparent");
      ctx!.fillStyle = grd;
      ctx!.beginPath();
      ctx!.arc(cx, cy, glowRadius, 0, Math.PI * 2);
      ctx!.fill();

      // Ring 1
      const ring1Radius = baseRadius * 1.3 * breathe;
      ctx!.strokeStyle = color.replace(")", " / 0.12)").replace("oklch(", "oklch(");
      ctx!.lineWidth = 1;
      ctx!.beginPath();
      ctx!.arc(cx, cy, ring1Radius, 0, Math.PI * 2);
      ctx!.stroke();

      // Ring 2 (rotating)
      const ring2Radius = baseRadius * 1.6 * breathe;
      const rot = t * 0.3;
      ctx!.strokeStyle = color.replace(")", " / 0.08)").replace("oklch(", "oklch(");
      ctx!.lineWidth = 0.5;
      ctx!.beginPath();
      ctx!.arc(cx, cy, ring2Radius, rot, rot + Math.PI * 1.5);
      ctx!.stroke();

      // Ring 3 (counter-rotating, dashed)
      const ring3Radius = baseRadius * 1.9 * breathe;
      ctx!.setLineDash([4, 8]);
      ctx!.strokeStyle = color.replace(")", " / 0.06)").replace("oklch(", "oklch(");
      ctx!.lineWidth = 0.5;
      ctx!.beginPath();
      ctx!.arc(cx, cy, ring3Radius, -rot * 0.7, -rot * 0.7 + Math.PI * 1.2);
      ctx!.stroke();
      ctx!.setLineDash([]);

      // Particles
      for (const p of particles) {
        p.angle += p.speed;
        p.angle += p.drift;
        const pr = baseRadius * p.radius * breathe + Math.sin(t + p.angle * 2) * 3;
        const px = cx + Math.cos(p.angle) * pr;
        const py = cy + Math.sin(p.angle) * pr;
        const po = p.opacity * (0.6 + Math.sin(t * 1.5 + p.angle) * 0.4);
        ctx!.fillStyle = color.replace(")", ` / ${po})`).replace("oklch(", "oklch(");
        ctx!.beginPath();
        ctx!.arc(px, py, p.size, 0, Math.PI * 2);
        ctx!.fill();
      }

      // Core orb
      const coreGrd = ctx!.createRadialGradient(
        cx - baseRadius * 0.15, cy - baseRadius * 0.15, 0,
        cx, cy, baseRadius
      );
      coreGrd.addColorStop(0, color.replace(")", " / 0.9)").replace("oklch(", "oklch("));
      coreGrd.addColorStop(0.6, color.replace(")", " / 0.6)").replace("oklch(", "oklch("));
      coreGrd.addColorStop(1, color.replace(")", " / 0.3)").replace("oklch(", "oklch("));
      ctx!.fillStyle = coreGrd;
      ctx!.beginPath();
      ctx!.arc(cx, cy, baseRadius * breathe, 0, Math.PI * 2);
      ctx!.fill();

      // Inner highlight
      const hlGrd = ctx!.createRadialGradient(
        cx - baseRadius * 0.2, cy - baseRadius * 0.2, 0,
        cx, cy, baseRadius * 0.6
      );
      hlGrd.addColorStop(0, "oklch(1 0 0 / 0.25)");
      hlGrd.addColorStop(1, "transparent");
      ctx!.fillStyle = hlGrd;
      ctx!.beginPath();
      ctx!.arc(cx, cy, baseRadius * 0.6 * breathe, 0, Math.PI * 2);
      ctx!.fill();

      // Thinking animation (orbiting dots)
      if (state === "thinking") {
        for (let i = 0; i < 3; i++) {
          const a = t * 2 + (i * Math.PI * 2) / 3;
          const r = baseRadius * 1.1;
          const dx = cx + Math.cos(a) * r;
          const dy = cy + Math.sin(a) * r;
          ctx!.fillStyle = color.replace(")", " / 0.7)").replace("oklch(", "oklch(");
          ctx!.beginPath();
          ctx!.arc(dx, dy, 2, 0, Math.PI * 2);
          ctx!.fill();
        }
      }

      animRef.current = requestAnimationFrame(draw);
    }

    draw();
    return () => cancelAnimationFrame(animRef.current);
  }, [size, state, color, particles]);

  return (
    <div
      className={`relative inline-flex items-center justify-center ${className}`}
      style={{ width: size * 1.8, height: size * 1.8 }}
    >
      <canvas
        ref={canvasRef}
        className={`absolute inset-0 ${interactive ? "cursor-pointer" : ""}`}
        onClick={onClick}
        style={{ filter: `drop-shadow(${glow.replace("0 0 ", "0 0 ")})` }}
      />
      {/* CSS glow ring for additional depth */}
      <div
        className="absolute rounded-full orb-breathe pointer-events-none"
        style={{
          width: size * 0.9,
          height: size * 0.9,
          boxShadow: glow,
          transition: "box-shadow 0.8s ease",
        }}
      />
    </div>
  );
}
