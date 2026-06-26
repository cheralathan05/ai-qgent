import { createFileRoute } from "@tanstack/react-router";
import { Shell, PageHeader, Section } from "@/components/apa/Shell";
import { useApa } from "@/lib/apa/store";

export const Route = createFileRoute("/knowledge/graph")({
  head: () => ({ meta: [{ title: "Knowledge Graph — APA-OS" }] }),
  component: GraphPage,
});

function GraphPage() {
  const world = useApa(s => s.world);
  const W = 720, H = 460;
  const cx = W / 2, cy = H / 2;
  const positions = new Map<string, { x: number; y: number }>();
  world.nodes.forEach((n, i) => {
    if (n.id === "self") { positions.set(n.id, { x: cx, y: cy }); return; }
    const angle = (i / (world.nodes.length - 1)) * Math.PI * 2;
    positions.set(n.id, { x: cx + Math.cos(angle) * 180, y: cy + Math.sin(angle) * 160 });
  });

  return (
    <Shell>
      <PageHeader
        eyebrow="Phase 03 · Graph"
        title="Knowledge Graph."
        lede="Documents, people, projects, deadlines — and the threads between them. The shape of what APA knows."
      />

      <Section title={`${world.nodes.length} nodes · ${world.edges.length} relationships`}>
        <div className="border hairline rounded-md overflow-hidden bg-surface/40">
          <svg viewBox={`0 0 ${W} ${H}`} className="w-full h-[480px]">
            {world.edges.map((e, i) => {
              const a = positions.get(e.from); const b = positions.get(e.to);
              if (!a || !b) return null;
              return <line key={i} x1={a.x} y1={a.y} x2={b.x} y2={b.y} stroke="var(--color-border)" strokeWidth={0.6} />;
            })}
            {world.nodes.map(n => {
              const p = positions.get(n.id)!;
              const self = n.id === "self";
              return (
                <g key={n.id}>
                  <circle cx={p.x} cy={p.y} r={self ? 8 : 4} fill={self ? "var(--color-accent)" : "var(--color-foreground)"} opacity={self ? 1 : 0.85} />
                  <text x={p.x} y={p.y - 10} textAnchor="middle" className="fill-foreground" style={{ fontSize: 10, fontFamily: "monospace" }}>{n.label}</text>
                </g>
              );
            })}
          </svg>
        </div>
      </Section>
    </Shell>
  );
}
