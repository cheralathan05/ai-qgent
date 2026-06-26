import { createFileRoute } from "@tanstack/react-router";
import { Shell, PageHeader, Section } from "@/components/apa/Shell";
import { useApa } from "@/lib/apa/store";
import { AGENT_LIST } from "@/lib/apa/agents";

export const Route = createFileRoute("/observatory")({
  head: () => ({ meta: [{ title: "AI Observatory — APA-OS V2" }] }),
  component: ObservatoryPage,
});

function ObservatoryPage() {
  const outcomes = useApa(s => s.outcomes);
  const memory = useApa(s => s.memory);
  const replay = useApa(s => s.replay);
  const goals = useApa(s => s.goals);

  const liveAgents = outcomes[0]?.agents ?? [];

  return (
    <Shell>
      <PageHeader
        eyebrow="Hidden Layer 13"
        title="AI Observatory."
        lede="Mission control. Live agent activity, memory churn, current reasoning, upcoming predictions — everything the system is thinking, in one room."
      />

      <Section>
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-px bg-[var(--color-border)] border hairline">
          <Tile label="Outcomes processed"      value={outcomes.length} />
          <Tile label="Memories held"           value={memory.length} />
          <Tile label="Recorded actions"        value={replay.length} />
          <Tile label="Active goals"            value={goals.length} />
          <Tile label="Agents available"        value={AGENT_LIST.length} />
          <Tile label="System confidence"       value={`${outcomes[0]?.confidence ?? 84}%`} />
        </div>
      </Section>

      <Section title="Live agent floor">
        {liveAgents.length === 0 ? (
          <p className="text-sm text-muted-foreground italic">Quiet. Run an outcome and watch the floor light up.</p>
        ) : (
          <div className="grid grid-cols-2 md:grid-cols-5 gap-px bg-[var(--color-border)] border hairline">
            {AGENT_LIST.map(a => {
              const run = liveAgents.find(x => x.agentId === a.id);
              const active = run?.status === "running";
              const done   = run?.status === "done";
              return (
                <div key={a.id} className="bg-background p-5">
                  <div className="flex items-center gap-2">
                    <span className={[
                      "h-1.5 w-1.5 rounded-full",
                      active ? "bg-accent apa-pulse" : done ? "bg-success" : "bg-muted-foreground/30",
                    ].join(" ")} />
                    <p className="text-[12px]">{a.name.replace(" Agent", "")}</p>
                  </div>
                  <p className="mt-3 font-mono text-[10px] text-muted-foreground">
                    {run?.status ?? "idle"}
                  </p>
                </div>
              );
            })}
          </div>
        )}
      </Section>
    </Shell>
  );
}

function Tile({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="bg-background p-7">
      <p className="font-mono text-[10px] uppercase tracking-[0.18em] text-muted-foreground">{label}</p>
      <p className="mt-3 font-display text-5xl tracking-tight">{value}</p>
    </div>
  );
}
