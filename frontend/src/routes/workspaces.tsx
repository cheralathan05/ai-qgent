import { createFileRoute } from "@tanstack/react-router";
import { Shell, PageHeader, Section } from "@/components/apa/Shell";
import { entStore, useEnt } from "@/lib/apa/enterprise";

export const Route = createFileRoute("/workspaces")({
  head: () => ({ meta: [{ title: "Workspaces — APA-OS" }] }),
  component: WorkspacesPage,
});

function WorkspacesPage() {
  const ws = useEnt(s => s.workspaces);
  const active = useEnt(s => s.activeWorkspaceId);
  return (
    <Shell>
      <PageHeader eyebrow="Boundaries" title="Workspaces."
        lede="Separate contexts for separate lives. Each has its own devices, knowledge, goals, workflows and permissions." />
      <Section>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {ws.map(w => (
            <button key={w.id}
              onClick={() => entStore.set(s => ({ ...s, activeWorkspaceId: w.id }))}
              className={["text-left rounded-lg border hairline p-5 transition",
                w.id === active ? "border-[color:var(--color-accent)] bg-surface/60" : "hover:bg-surface/40"].join(" ")}>
              <p className="text-[9px] uppercase tracking-[0.22em] text-accent">{w.kind}</p>
              <p className="mt-2 font-display text-2xl">{w.name}</p>
              <p className="mt-3 text-[11.5px] text-muted-foreground leading-relaxed">
                Devices · Knowledge · Goals · Workflows · Settings · Permissions
              </p>
              {w.id === active && <p className="mt-4 text-[10px] uppercase tracking-[0.22em] text-accent">Active</p>}
            </button>
          ))}
          <button
            onClick={() => entStore.set(s => ({
              ...s,
              workspaces: [...s.workspaces, { id: crypto.randomUUID(), name: "New workspace", kind: "custom" }]
            }))}
            className="rounded-lg border hairline border-dashed p-5 text-left text-muted-foreground hover:text-foreground hover:bg-surface/40"
          >
            <p className="text-[9px] uppercase tracking-[0.22em]">New</p>
            <p className="mt-2 font-display text-2xl">+ Add workspace</p>
            <p className="mt-3 text-[11.5px]">Studio, side project, family — anything that needs its own world.</p>
          </button>
        </div>
      </Section>
    </Shell>
  );
}
