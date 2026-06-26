import { createFileRoute, Link } from "@tanstack/react-router";
import { Shell, PageHeader, Section } from "@/components/apa/Shell";

export const Route = createFileRoute("/knowledge")({
  head: () => ({ meta: [{ title: "Knowledge — APA-OS" }] }),
  component: KnowledgePage,
});

function KnowledgePage() {
  return (
    <Shell>
      <PageHeader
        eyebrow="Phase 03 · Knowledge OS"
        title="Knowledge."
        lede="Your files, notes, and documents — read, embedded, and remembered. The substrate APA reasons from."
      />

      <Section title="Overview">
        <div className="grid sm:grid-cols-4 gap-5">
          <Stat label="Sources" value="6" accent />
          <Stat label="Documents" value="1,284" />
          <Stat label="Embeddings" value="42,113" />
          <Stat label="Last sync" value="2m ago" />
        </div>
      </Section>

      <Section title="Explore">
        <ul className="grid sm:grid-cols-2 gap-3">
          {[
            { to: "/knowledge/search", label: "Search", hint: "Semantic · hybrid" },
            { to: "/knowledge/sources", label: "Sources", hint: "Drive · GitHub · Notion" },
            { to: "/knowledge/graph", label: "Graph", hint: "How everything connects" },
            { to: "/knowledge/chat", label: "Chat with knowledge", hint: "RAG · cited" },
          ].map(it => (
            <li key={it.to}>
              <Link to={it.to} className="block border hairline rounded-md p-5 hover:border-accent transition">
                <p className="text-[9px] uppercase tracking-[0.22em] text-accent">{it.hint}</p>
                <p className="mt-1 font-display text-[18px]">{it.label}</p>
              </Link>
            </li>
          ))}
        </ul>
      </Section>
    </Shell>
  );
}

function Stat({ label, value, accent }: { label: string; value: string; accent?: boolean }) {
  return (
    <div>
      <p className="text-[9px] uppercase tracking-[0.22em] text-muted-foreground">{label}</p>
      <p className={`mt-2 font-display text-[22px] ${accent ? "text-accent" : ""}`}>{value}</p>
    </div>
  );
}
