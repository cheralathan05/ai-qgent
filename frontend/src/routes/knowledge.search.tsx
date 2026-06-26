import { createFileRoute } from "@tanstack/react-router";
import { useState, useMemo } from "react";
import { Shell, PageHeader, Section } from "@/components/apa/Shell";

export const Route = createFileRoute("/knowledge/search")({
  head: () => ({ meta: [{ title: "Knowledge Search — APA-OS" }] }),
  component: SearchPage,
});

const DOCS = [
  { id: "d1", title: "ATM Protocol — design notes", source: "Drive", snippet: "Three-way handshake, retry budget, …", score: 0.94 },
  { id: "d2", title: "Compilers Unit 4 — code gen", source: "Notion", snippet: "Activation records, register allocation…", score: 0.91 },
  { id: "d3", title: "Resume — Cheralathan", source: "Drive", snippet: "B.Tech CSE · projects: ATM, Eyesona…", score: 0.83 },
  { id: "d4", title: "Placement shortlist (Q3)", source: "Drive", snippet: "12 product companies matched on stack…", score: 0.78 },
  { id: "d5", title: "Cohort schedule — Sem 5", source: "Calendar", snippet: "Exams, labs, projects…", score: 0.72 },
];

function SearchPage() {
  const [q, setQ] = useState("");
  const [filter, setFilter] = useState<string>("all");
  const results = useMemo(() => {
    const ql = q.toLowerCase();
    return DOCS
      .filter(d => filter === "all" || d.source === filter)
      .filter(d => !ql || d.title.toLowerCase().includes(ql) || d.snippet.toLowerCase().includes(ql));
  }, [q, filter]);

  const sources = ["all", "Drive", "Notion", "Calendar"];

  return (
    <Shell>
      <PageHeader
        eyebrow="Phase 03 · Search"
        title="Knowledge Search."
        lede="Semantic, hybrid, ranked. Ask in your words — get the file, the line, the citation."
      />

      <Section title="Query">
        <input
          value={q}
          onChange={e => setQ(e.target.value)}
          placeholder="Find anything…"
          className="w-full bg-transparent border hairline rounded-md px-4 py-3 text-[14px] outline-none focus:border-accent"
        />
        <div className="mt-3 flex gap-2">
          {sources.map(s => (
            <button key={s} onClick={() => setFilter(s)}
              className={`px-3 py-1 border hairline rounded text-[10px] uppercase tracking-wider transition
                ${filter === s ? "text-accent border-accent" : "text-muted-foreground hover:text-foreground"}`}>
              {s}
            </button>
          ))}
        </div>
      </Section>

      <Section title={`Results · ${results.length}`}>
        <ul className="divide-y hairline">
          {results.map(d => (
            <li key={d.id} className="py-4">
              <div className="flex items-baseline justify-between gap-4">
                <p className="font-display text-[15px]">{d.title}</p>
                <span className="font-mono text-[10px] text-accent">{Math.round(d.score * 100)}%</span>
              </div>
              <p className="mt-1 text-[12px] text-muted-foreground">{d.snippet}</p>
              <p className="mt-1 text-[10px] uppercase tracking-wider text-muted-foreground/60">{d.source}</p>
            </li>
          ))}
          {results.length === 0 && <li className="py-6 text-[12px] text-muted-foreground italic">No matches.</li>}
        </ul>
      </Section>
    </Shell>
  );
}
