import { createFileRoute } from "@tanstack/react-router";
import { useState } from "react";
import { Shell, PageHeader, Section } from "@/components/apa/Shell";

export const Route = createFileRoute("/knowledge/chat")({
  head: () => ({ meta: [{ title: "RAG Chat — APA-OS" }] }),
  component: RagChatPage,
});

interface Turn { id: string; who: "you" | "apa"; text: string; citations?: { title: string; source: string }[]; }

const SEED: Turn[] = [
  { id: "t1", who: "you", text: "What did I write about register allocation last week?" },
  { id: "t2", who: "apa", text: "Your Compilers Unit 4 notes describe linear-scan and graph-coloring approaches. You flagged spill cost heuristics as a weak area.",
    citations: [
      { title: "Compilers Unit 4 — code gen", source: "Notion" },
      { title: "Weekly review · Nov 14", source: "Drive" },
    ]},
];

function RagChatPage() {
  const [turns, setTurns] = useState<Turn[]>(SEED);
  const [q, setQ] = useState("");

  function ask() {
    if (!q.trim()) return;
    const id = Math.random().toString(36).slice(2);
    const my: Turn = { id, who: "you", text: q };
    const reply: Turn = {
      id: id + "r", who: "apa",
      text: `Pulled 3 sources matching "${q}". Top result suggests revisiting your ATM Protocol diagram and the placement shortlist.`,
      citations: [
        { title: "ATM Protocol — design notes", source: "Drive" },
        { title: "Placement shortlist (Q3)", source: "Drive" },
      ],
    };
    setTurns(t => [...t, my, reply]);
    setQ("");
  }

  return (
    <Shell>
      <PageHeader
        eyebrow="Phase 03 · RAG"
        title="Chat with your knowledge."
        lede="Ask. APA retrieves, reasons, cites. Every answer points back to the source line."
      />

      <Section title="Conversation">
        <ul className="space-y-5">
          {turns.map(t => (
            <li key={t.id}>
              <p className="text-[9px] uppercase tracking-[0.22em] text-accent">{t.who}</p>
              <p className="mt-1 text-[14px] leading-relaxed">{t.text}</p>
              {t.citations && (
                <ul className="mt-2 flex flex-wrap gap-2">
                  {t.citations.map((c, i) => (
                    <li key={i} className="px-2.5 py-1 border hairline rounded text-[10px] text-muted-foreground">
                      {c.title} · <span className="text-accent">{c.source}</span>
                    </li>
                  ))}
                </ul>
              )}
            </li>
          ))}
        </ul>
      </Section>

      <Section title="Ask">
        <div className="flex gap-2">
          <input
            value={q}
            onChange={e => setQ(e.target.value)}
            onKeyDown={e => e.key === "Enter" && ask()}
            placeholder="Ask anything in your knowledge…"
            className="flex-1 bg-transparent border hairline rounded-md px-4 py-3 text-[14px] outline-none focus:border-accent"
          />
          <button onClick={ask} className="px-5 border hairline rounded-md text-[11px] uppercase tracking-[0.22em] hover:text-accent hover:border-accent">Send</button>
        </div>
      </Section>
    </Shell>
  );
}
