import { createFileRoute, Link } from "@tanstack/react-router";
import { Shell, PageHeader, Section } from "@/components/apa/Shell";

export const Route = createFileRoute("/documents/$id")({
  head: () => ({ meta: [{ title: "Document — APA-OS" }] }),
  component: DocumentPage,
});

const SAMPLE = {
  title: "ATM Protocol — design notes",
  source: "Drive · College › Sem 5",
  body: `# ATM Protocol\n\nThree-way handshake with bounded retries.\n\n## Goals\n- Reliable delivery under 220ms\n- Idempotent client side\n- Verifiable receipt trail\n\n## Open questions\n- Backoff curve for partial network partitions\n- Schema versioning across mobile + backend`,
  highlights: ["Three-way handshake", "Verifiable receipt trail"],
  citations: 3,
};

function DocumentPage() {
  const { id } = Route.useParams();
  return (
    <Shell>
      <PageHeader
        eyebrow={`Doc · ${id}`}
        title={SAMPLE.title}
        lede={SAMPLE.source}
      />

      <Section title="Content">
        <pre className="text-[13px] leading-relaxed whitespace-pre-wrap font-sans border hairline rounded-md p-5 bg-surface/40">
          {SAMPLE.body}
        </pre>
      </Section>

      <Section title={`Highlights · ${SAMPLE.highlights.length}`}>
        <ul className="space-y-1.5">
          {SAMPLE.highlights.map((h, i) => (
            <li key={i} className="text-[12.5px] text-foreground/90">— {h}</li>
          ))}
        </ul>
      </Section>

      <div className="px-7 py-6 border-t hairline">
        <Link to="/knowledge/search" className="text-[10px] uppercase tracking-[0.22em] text-muted-foreground hover:text-accent">← back to search</Link>
      </div>
    </Shell>
  );
}
