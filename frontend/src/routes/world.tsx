import { createFileRoute } from "@tanstack/react-router";
import { useMemo, useState } from "react";
import { Shell, PageHeader, Section } from "@/components/apa/Shell";
import { useApa } from "@/lib/apa/store";
import type { WorldNode } from "@/lib/apa/types";

export const Route = createFileRoute("/world")({
  head: () => ({ meta: [{ title: "World Model — APA-OS V3" }] }),
  component: WorldPage,
});

const KIND_COLOR: Record<string, string> = {
  self: "var(--color-accent)",
  person: "var(--color-foreground)",
  place: "var(--color-muted-foreground)",
  project: "var(--color-ochre)",
  deadline: "var(--color-warn)",
  goal: "var(--color-success)",
  device: "var(--color-muted-foreground)",
  subject: "var(--color-foreground)",
  app: "var(--color-muted-foreground)",
};

function WorldPage() {
  const { nodes, edges } = useApa(s => s.world);
  const outcomes = useApa(s => s.outcomes);
  const focused = outcomes[0];
  const highlights = new Set(focused?.worldHighlights ?? []);

  const [query, setQuery] = useState("");
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const q = query.toLowerCase().trim();
  const visibleIds = useMemo(() => {
    if (!q) return new Set(nodes.map(n => n.id));
    const matches = nodes.filter(n => n.label.toLowerCase().includes(q) || n.kind.includes(q));
    const ids = new Set(matches.map(n => n.id));
    matches.forEach(m => {
      edges.forEach(e => {
        if (e.from === m.id) ids.add(e.to);
        if (e.to === m.id) ids.add(e.from);
      });
    });
    return ids;
  }, [q, nodes, edges]);

  // radial layout
  const cx = 380, cy = 320, r = 240;
  const others = nodes.filter(n => n.kind !== "self");
  const positioned = others.map((n, i) => {
    const angle = (i / others.length) * Math.PI * 2 - Math.PI / 2;
    return { ...n, x: cx + Math.cos(angle) * r, y: cy + Math.sin(angle) * r };
  });
  const self = nodes.find(n => n.kind === "self");
  const pos = new Map<string, { x: number; y: number }>();
  if (self) pos.set(self.id, { x: cx, y: cy });
  positioned.forEach(p => pos.set(p.id, { x: p.x, y: p.y }));

  const selected = selectedId ? nodes.find(n => n.id === selectedId) ?? null : null;
  const selectedEdges = selected ? edges.filter(e => e.from === selected.id || e.to === selected.id) : [];

  return (
    <Shell>
      <PageHeader
        eyebrow="Hidden Layer 02"
        title="World Model."
        lede="A live map of the people, places, projects, devices, subjects, apps and deadlines that make up your reality. Every action in APA-OS flows through this graph."
      />

      <Section
        title="Interactive graph"
        aside={
          <input
            value={query}
            onChange={e => setQuery(e.target.value)}
            placeholder="Search world…"
            className="bg-surface/60 border hairline rounded-md px-3 py-1.5 text-[12px] outline-none w-[220px]"
          />
        }
      >
        <div className="grid grid-cols-1 lg:grid-cols-[1fr_340px] gap-px bg-[var(--color-border)] border hairline">
          <div className="bg-background overflow-hidden">
            <svg viewBox="0 0 760 640" className="w-full h-auto">
              {edges.map((e, i) => {
                const a = pos.get(e.from), b = pos.get(e.to);
                if (!a || !b) return null;
                const visible = visibleIds.has(e.from) && visibleIds.has(e.to);
                const isHighlighted = focused && highlights.has(e.from) && highlights.has(e.to);
                return (
                  <g key={i}>
                    <line
                      x1={a.x} y1={a.y} x2={b.x} y2={b.y}
                      stroke={isHighlighted ? "var(--color-accent)" : "var(--color-border-strong)"}
                      strokeWidth={isHighlighted ? 1.4 : 0.6}
                      opacity={visible ? (isHighlighted ? 0.9 : 0.35) : 0.06}
                    />
                  </g>
                );
              })}
              {[self, ...positioned].filter(Boolean).map(n => {
                const p = pos.get(n!.id)!;
                const isSelf = n!.kind === "self";
                const visible = visibleIds.has(n!.id);
                const isHighlighted = focused && highlights.has(n!.id);
                return (
                  <g
                    key={n!.id}
                    transform={`translate(${p.x},${p.y})`}
                    opacity={visible ? 1 : 0.18}
                    style={{ cursor: "pointer" }}
                    onClick={() => setSelectedId(n!.id)}
                  >
                    <circle
                      r={isSelf ? 11 : 5.5}
                      fill={KIND_COLOR[n!.kind]}
                      opacity={isSelf ? 1 : 0.95}
                    />
                    {isHighlighted && (
                      <circle r={14} fill="none" stroke="var(--color-accent)" strokeWidth="1.4" className="apa-pulse" />
                    )}
                    {isSelf && (
                      <circle r={24} fill="none" stroke="var(--color-accent)" strokeOpacity="0.4" className="apa-pulse" />
                    )}
                    <text x={isSelf ? 0 : 10} y={isSelf ? -22 : 4}
                          fontFamily="var(--font-sans)" fontSize={isSelf ? 13 : 11}
                          textAnchor={isSelf ? "middle" : "start"}
                          fill="var(--color-foreground)">{n!.label}</text>
                    <text x={isSelf ? 0 : 10} y={isSelf ? -38 : 17}
                          fontFamily="var(--font-mono)" fontSize={9}
                          textAnchor={isSelf ? "middle" : "start"}
                          fill="var(--color-muted-foreground)" letterSpacing="1.5">
                      {n!.kind.toUpperCase()}
                    </text>
                  </g>
                );
              })}
              {focused && (
                <text x={20} y={28} fontSize="10" fontFamily="var(--font-mono)" letterSpacing="1.8"
                      fill="var(--color-accent)">AI REASONING PATH · {focused.text}</text>
              )}
            </svg>
          </div>

          <aside className="bg-background p-6 min-h-[400px]">
            {selected ? <NodePanel node={selected} edges={selectedEdges} nodes={nodes} onSelect={setSelectedId} />
              : <DefaultLegend />}
          </aside>
        </div>
      </Section>

      <Section title="Live agent usage">
        <ul className="grid grid-cols-1 md:grid-cols-3 gap-px bg-[var(--color-border)] border hairline">
          {[
            { agent: "Memory", using: "Deepak · ATM Protocol" },
            { agent: "Planner", using: "Sem 5 Exams" },
            { agent: "Communication", using: "WhatsApp" },
          ].map(u => (
            <li key={u.agent} className="bg-background p-5">
              <p className="font-mono text-[10px] uppercase tracking-wider text-accent">{u.agent} agent</p>
              <p className="mt-2 text-[13px]">Using <span className="text-foreground">{u.using}</span></p>
            </li>
          ))}
        </ul>
      </Section>
    </Shell>
  );
}

function NodePanel({ node, edges, nodes, onSelect }: {
  node: WorldNode;
  edges: { from: string; to: string; relation: string; weight?: number }[];
  nodes: WorldNode[];
  onSelect: (id: string) => void;
}) {
  return (
    <>
      <p className="font-mono text-[10px] uppercase tracking-[0.22em] text-accent">{node.kind}</p>
      <p className="mt-2 font-display text-2xl">{node.label}</p>
      {node.meta && (
        <ul className="mt-3 space-y-1.5">
          {Object.entries(node.meta).map(([k, v]) => (
            <li key={k} className="flex items-baseline justify-between text-[12px]">
              <span className="font-mono text-[9.5px] uppercase tracking-wider text-muted-foreground">{k}</span>
              <span>{v}</span>
            </li>
          ))}
        </ul>
      )}
      <div className="mt-5">
        <p className="font-mono text-[10px] uppercase tracking-wider text-muted-foreground">Connections</p>
        <ul className="mt-2 space-y-1.5">
          {edges.map((e, i) => {
            const otherId = e.from === node.id ? e.to : e.from;
            const other = nodes.find(n => n.id === otherId);
            return (
              <li key={i}>
                <button
                  onClick={() => onSelect(otherId)}
                  className="w-full text-left flex items-baseline justify-between text-[12px] hover:text-accent transition"
                >
                  <span>{other?.label}</span>
                  <span className="font-mono text-[9.5px] uppercase tracking-wider text-muted-foreground">{e.relation}</span>
                </button>
                {e.weight && (
                  <div className="mt-1 h-[2px] bg-[var(--color-border)] rounded">
                    <div className="h-full bg-accent" style={{ width: `${e.weight}%` }} />
                  </div>
                )}
              </li>
            );
          })}
        </ul>
      </div>
      <div className="mt-5">
        <p className="font-mono text-[10px] uppercase tracking-wider text-muted-foreground">Actions</p>
        <div className="mt-2 flex flex-wrap gap-1.5">
          {["Message","Share file","Schedule","View timeline","Create task"].map(a => (
            <button key={a} className="rounded-md border hairline px-2.5 py-1 text-[11px] hover:border-accent hover:text-accent transition">{a}</button>
          ))}
        </div>
      </div>
    </>
  );
}

function DefaultLegend() {
  return (
    <>
      <p className="font-mono text-[10px] uppercase tracking-[0.22em] text-muted-foreground">Legend</p>
      <ul className="mt-3 space-y-1.5 text-[12px]">
        {Object.entries(KIND_COLOR).map(([k, c]) => (
          <li key={k} className="flex items-center gap-3">
            <span className="h-2 w-2 rounded-full" style={{ background: c }} />
            <span className="capitalize">{k}</span>
          </li>
        ))}
      </ul>
      <p className="mt-6 text-[12px] text-muted-foreground leading-relaxed">
        Click any node. When you mention "Deepak", the system doesn't search — it knows. Every action APA-OS takes traces a path through this graph.
      </p>
    </>
  );
}
