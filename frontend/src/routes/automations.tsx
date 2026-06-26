import { createFileRoute } from "@tanstack/react-router";
import { useState } from "react";
import { Shell, PageHeader, Section } from "@/components/apa/Shell";

export const Route = createFileRoute("/automations")({
  head: () => ({ meta: [{ title: "Automations — APA-OS" }] }),
  component: AutomationsPage,
});

interface Rule { id: string; trigger: string; condition: string; action: string; schedule?: string; on: boolean; }

const SEED: Rule[] = [
  { id: "a1", trigger: "Calendar event starts", condition: "Tagged 'focus'", action: "Phone → focus mode, mute group chats", on: true },
  { id: "a2", trigger: "Daily", condition: "08:30 AM",                       action: "Brief: today's exam readiness", schedule: "Recurring", on: true },
  { id: "a3", trigger: "Battery < 20%", condition: "Studying mode",          action: "Notify you · suggest charger near desk", on: false },
];

function AutomationsPage() {
  const [rules, setRules] = useState<Rule[]>(SEED);
  function toggle(id: string) { setRules(rs => rs.map(r => r.id === id ? { ...r, on: !r.on } : r)); }

  return (
    <Shell>
      <PageHeader
        eyebrow="Phase 05 · Automation"
        title="Automations."
        lede="Triggers, conditions, actions, schedules. The silent rules that keep your life moving in the background."
      />

      <Section title={`Rules · ${rules.length}`}>
        <ul className="space-y-3">
          {rules.map(r => (
            <li key={r.id} className="border hairline rounded-md p-5 flex items-start justify-between gap-5">
              <div className="flex-1">
                <p className="text-[9px] uppercase tracking-[0.22em] text-accent">when</p>
                <p className="mt-1 text-[13px]">{r.trigger} · <span className="text-muted-foreground">{r.condition}</span></p>
                <p className="mt-3 text-[9px] uppercase tracking-[0.22em] text-accent">then</p>
                <p className="mt-1 text-[13px]">{r.action}</p>
                {r.schedule && <p className="mt-2 text-[10px] uppercase tracking-wider text-muted-foreground">{r.schedule}</p>}
              </div>
              <button onClick={() => toggle(r.id)}
                className={`text-[10px] uppercase tracking-[0.22em] px-3 py-1.5 border hairline rounded ${r.on ? "text-accent border-accent" : "text-muted-foreground"}`}>
                {r.on ? "on" : "off"}
              </button>
            </li>
          ))}
        </ul>
      </Section>
    </Shell>
  );
}
