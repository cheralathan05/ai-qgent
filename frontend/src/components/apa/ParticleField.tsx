import { useEffect, useRef } from "react";

interface ParticleFieldProps {
  className?: string;
  count?: number;
  color?: string;
  speed?: number;
  opacity?: number;
}

export function ParticleField({
  className = "",
  count = 50,
  color = "oklch(0.78 0.11 70)",
  speed = 0.3,
  opacity = 0.4,
}: ParticleFieldProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const animRef = useRef<number>(0);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    let w = 0;
    let h = 0;

    const particles = Array.from({ length: count }, () => ({
      x: Math.random() * 2000,
      y: Math.random() * 2000,
      vx: (Math.random() - 0.5) * speed,
      vy: -Math.random() * speed - 0.1,
      size: Math.random() * 2 + 0.3,
      opacity: Math.random() * opacity,
      life: Math.random(),
    }));

    function resize() {
      const dpr = window.devicePixelRatio || 1;
      w = window.innerWidth;
      h = window.innerHeight;
      canvas!.width = w * dpr;
      canvas!.height = h * dpr;
      canvas!.style.width = `${w}px`;
      canvas!.style.height = `${h}px`;
      ctx!.scale(dpr, dpr);
    }

    function draw() {
      ctx!.clearRect(0, 0, w, h);

      for (const p of particles) {
        p.x += p.vx;
        p.y += p.vy;
        p.life += 0.001;

        if (p.y < -10 || p.life > 1) {
          p.x = Math.random() * w;
          p.y = h + 10;
          p.life = 0;
        }
        if (p.x < -10) p.x = w + 10;
        if (p.x > w + 10) p.x = -10;

        const fadeIn = Math.min(p.life * 5, 1);
        const fadeOut = Math.max(1 - (p.life - 0.7) / 0.3, 0);
        const alpha = p.opacity * fadeIn * (p.life > 0.7 ? fadeOut : 1);

        ctx!.fillStyle = color.replace(")", ` / ${alpha})`).replace("oklch(", "oklch(");
        ctx!.beginPath();
        ctx!.arc(p.x, p.y, p.size, 0, Math.PI * 2);
        ctx!.fill();
      }

      // Draw subtle connections between nearby particles
      for (let i = 0; i < particles.length; i++) {
        for (let j = i + 1; j < particles.length; j++) {
          const dx = particles[i].x - particles[j].x;
          const dy = particles[i].y - particles[j].y;
          const dist = Math.sqrt(dx * dx + dy * dy);
          if (dist < 100) {
            const alpha = (1 - dist / 100) * 0.06;
            ctx!.strokeStyle = color.replace(")", ` / ${alpha})`).replace("oklch(", "oklch(");
            ctx!.lineWidth = 0.5;
            ctx!.beginPath();
            ctx!.moveTo(particles[i].x, particles[i].y);
            ctx!.lineTo(particles[j].x, particles[j].y);
            ctx!.stroke();
          }
        }
      }

      animRef.current = requestAnimationFrame(draw);
    }

    resize();
    draw();
    window.addEventListener("resize", resize);

    return () => {
      cancelAnimationFrame(animRef.current);
      window.removeEventListener("resize", resize);
    };
  }, [count, color, speed, opacity]);

  return (
    <canvas
      ref={canvasRef}
      className={`fixed inset-0 pointer-events-none ${className}`}
      style={{ zIndex: 0 }}
    />
  );
}
