import { createFileRoute } from "@tanstack/react-router";
import { useState } from "react";
import { Shell, PageHeader, Section } from "@/components/apa/Shell";

export const Route = createFileRoute("/approvals")({
  head: () => ({ meta: [{ title: "Approvals — APA-OS" }] }),
  component: ApprovalsPage,
});

interface Pending { id: string; agent: string; action: string; reason: string; impact: string; }

const SEED: Pending[] = [
  { id: "a1", agent: "communication", action: "Send draft to Deepak", reason: "Outcome verified · recipient resolved.", impact: "Outbound · WhatsApp" },
  { id: "a2", agent: "automation", action: "Block 8–10 PM focus", reason: "Aligns with study peak window.", impact: "Calendar · today" },
  { id: "a3", agent: "device", action: "Open Compilers Unit 4 PDF on MacBook", reason: "Required for tonight's revision sprint.", impact: "Drive · safe" },
];

function ApprovalsPage() {
  const [items, setItems] = useState<Pending[]>(SEED);
  const [audit, setAudit] = useState<{ id: string; verb: "approved" | "rejected"; at: number; label: string }[]>([]);

  function decide(p: Pending, verb: "approved" | "rejected") {
    setItems(xs => xs.filter(x => x.id !== p.id));
    setAudit(xs => [{ id: p.id + verb, verb, at: Date.now(), label: p.action }, ...xs]);
  }

  return (
    <Shell>
      <PageHeader
        eyebrow="Phase 01 · Trust"
        title="Approvals."
        lede="Actions waiting on your one-tap consent. Read the reason. Decide. The audit trail keeps everything honest."
      />

      <Section title={`Pending · ${items.length}`}>
        {items.length === 0 ? (
          <p className="text-[12px] text-muted-foreground italic">Inbox zero. Nothing waiting.</p>
        ) : (
          <ul className="space-y-3">
            {items.map(p => (
              <li key={p.id} className="border hairline rounded-md p-5">
                <p className="text-[9px] uppercase tracking-[0.22em] text-accent">{p.agent}</p>
                <p className="mt-1 font-display text-[18px]">{p.action}</p>
                <p className="mt-2 text-[12px] text-muted-foreground">{p.reason}</p>
                <p className="mt-1 text-[10px] uppercase tracking-wider text-muted-foreground">{p.impact}</p>
                <div className="mt-4 flex gap-2 text-[10px] uppercase tracking-[0.22em]">
                  <button onClick={() => decide(p, "approved")} className="px-3 py-1.5 border hairline rounded text-foreground hover:text-accent hover:border-accent">Approve</button>
                  <button onClick={() => decide(p, "rejected")} className="px-3 py-1.5 border hairline rounded text-muted-foreground hover:text-destructive hover:border-destructive">Reject</button>
                </div>
              </li>
            ))}
          </ul>
        )}
      </Section>

      <Section title="Audit trail">
        {audit.length === 0 ? (
          <p className="text-[12px] text-muted-foreground italic">No decisions yet.</p>
        ) : (
          <ul className="divide-y hairline">
            {audit.map(a => (
              <li key={a.id} className="py-2.5 grid grid-cols-[120px_80px_1fr] gap-4 text-[12px] items-baseline">
                <span className="font-mono text-[10px] text-muted-foreground">{new Date(a.at).toLocaleTimeString()}</span>
                <span className={a.verb === "approved" ? "text-[color:var(--color-success)]" : "text-destructive"}>{a.verb}</span>
                <span>{a.label}</span>
              </li>
            ))}
          </ul>
        )}
      </Section>
    </Shell>
  );
}
