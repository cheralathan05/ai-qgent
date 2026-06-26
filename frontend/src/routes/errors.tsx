import { createFileRoute } from "@tanstack/react-router";
import { Shell, PageHeader, Section } from "@/components/apa/Shell";
import { useEnt } from "@/lib/apa/enterprise";

export const Route = createFileRoute("/errors")({
  head: () => ({ meta: [{ title: "Error Center — APA-OS" }] }),
  component: ErrorsPage,
});

function ErrorsPage() {
  const errors = useEnt(s => s.errors);
  return (
    <Shell>
      <PageHeader eyebrow="Reliability" title="Global Error Center."
        lede="Failures across API, devices, workflows, knowledge and sockets — each with a recovery path." />
      <Section>
        <table className="w-full text-[12.5px]">
          <thead>
            <tr className="text-left text-[10px] uppercase tracking-[0.18em] text-muted-foreground border-b hairline">
              <th className="py-2 font-normal">When</th>
              <th className="py-2 font-normal">Area</th>
              <th className="py-2 font-normal">Failure</th>
              <th className="py-2 font-normal">Recovery</th>
              <th className="py-2 font-normal">Status</th>
            </tr>
          </thead>
          <tbody>
            {errors.map(e => (
              <tr key={e.id} className="border-b hairline">
                <td className="py-3 font-mono text-[10.5px] text-muted-foreground">{new Date(e.at).toLocaleString()}</td>
                <td className="py-3 font-mono text-[10.5px] uppercase tracking-wider text-accent">{e.area}</td>
                <td className="py-3">{e.title}</td>
                <td className="py-3 text-muted-foreground">{e.recovery ?? "—"}</td>
                <td className="py-3">
                  <span className="font-mono text-[9px] uppercase tracking-wider"
                    style={{ color: e.resolved ? "var(--color-success)" : "var(--color-warn)" }}>
                    {e.resolved ? "resolved" : "open"}
                  </span>
                </td>
              </tr>
            ))}
            {errors.length === 0 && (
              <tr><td colSpan={5} className="py-10 text-center text-muted-foreground italic">No incidents.</td></tr>
            )}
          </tbody>
        </table>
      </Section>
    </Shell>
  );
}
