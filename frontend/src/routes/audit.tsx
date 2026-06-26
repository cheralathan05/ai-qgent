import { createFileRoute } from "@tanstack/react-router";
import { Shell, PageHeader, Section } from "@/components/apa/Shell";
import { useEnt } from "@/lib/apa/enterprise";

export const Route = createFileRoute("/audit")({
  head: () => ({ meta: [{ title: "Audit Center — APA-OS" }] }),
  component: AuditPage,
});

function AuditPage() {
  const activity = useEnt(s => s.activity);
  const ws = useEnt(s => s.workspaces.find(w => w.id === s.activeWorkspaceId)?.name ?? "—");
  return (
    <Shell>
      <PageHeader eyebrow="Provenance" title="Audit Center."
        lede="Every action — who, when, where it came from, what it touched, what it produced." />
      <Section>
        <table className="w-full text-[12.5px]">
          <thead>
            <tr className="text-left text-[10px] uppercase tracking-[0.18em] text-muted-foreground border-b hairline">
              <th className="py-2 font-normal">Time</th>
              <th className="py-2 font-normal">User</th>
              <th className="py-2 font-normal">Source</th>
              <th className="py-2 font-normal">Action</th>
              <th className="py-2 font-normal">Workspace</th>
              <th className="py-2 font-normal">Result</th>
            </tr>
          </thead>
          <tbody>
            {activity.map(a => (
              <tr key={a.id} className="border-b hairline">
                <td className="py-2.5 font-mono text-[10.5px] text-muted-foreground">{new Date(a.at).toLocaleString()}</td>
                <td className="py-2.5">you</td>
                <td className="py-2.5 font-mono text-[10.5px] uppercase tracking-wider text-accent">{a.source ?? a.kind}</td>
                <td className="py-2.5">{a.title}</td>
                <td className="py-2.5 text-muted-foreground">{ws}</td>
                <td className="py-2.5"><span className="font-mono text-[9px] uppercase tracking-wider" style={{ color: "var(--color-success)" }}>ok</span></td>
              </tr>
            ))}
          </tbody>
        </table>
      </Section>
    </Shell>
  );
}
