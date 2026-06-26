import { createFileRoute } from "@tanstack/react-router";
import { Shell, PageHeader, Section } from "@/components/apa/Shell";

export const Route = createFileRoute("/knowledge/sources")({
  head: () => ({ meta: [{ title: "Knowledge Sources — APA-OS" }] }),
  component: SourcesPage,
});

const SOURCES = [
  { name: "Google Drive", status: "connected" as const, docs: 612, lastSync: "2m ago" },
  { name: "OneDrive",     status: "available" as const, docs: 0,   lastSync: "—" },
  { name: "GitHub",       status: "connected" as const, docs: 384, lastSync: "6m ago" },
  { name: "GitLab",       status: "available" as const, docs: 0,   lastSync: "—" },
  { name: "Notion",       status: "connected" as const, docs: 211, lastSync: "11m ago" },
  { name: "Dropbox",      status: "available" as const, docs: 0,   lastSync: "—" },
  { name: "Local Files",  status: "connected" as const, docs: 77,  lastSync: "1h ago" },
];

function SourcesPage() {
  return (
    <Shell>
      <PageHeader
        eyebrow="Phase 03 · Sources"
        title="Knowledge Sources."
        lede="Where APA's knowledge comes from. Connect once — APA keeps everything indexed in the background."
      />

      <Section title={`Connected · ${SOURCES.filter(s => s.status === "connected").length}`}>
        <ul className="grid sm:grid-cols-2 gap-3">
          {SOURCES.map(s => (
            <li key={s.name} className="border hairline rounded-md p-4 flex items-center justify-between">
              <div>
                <p className="font-display text-[15px]">{s.name}</p>
                <p className="mt-0.5 text-[10px] uppercase tracking-wider text-muted-foreground">
                  {s.docs} docs · synced {s.lastSync}
                </p>
              </div>
              <span className={`text-[10px] uppercase tracking-[0.22em] ${s.status === "connected" ? "text-[color:var(--color-success)]" : "text-muted-foreground"}`}>
                {s.status}
              </span>
            </li>
          ))}
        </ul>
      </Section>
    </Shell>
  );
}
