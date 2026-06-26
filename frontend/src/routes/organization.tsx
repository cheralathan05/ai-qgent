import { createFileRoute } from "@tanstack/react-router";
import { Shell, PageHeader, Section } from "@/components/apa/Shell";

export const Route = createFileRoute("/organization")({
  head: () => ({ meta: [{ title: "Organization — APA-OS" }] }),
  component: OrgPage,
});

function OrgPage() {
  return (
    <Shell>
      <PageHeader
        eyebrow="Phase 05 · Autonomous Org"
        title="Organization."
        lede="When agents act together as your team — projects, clients, revenue, documents — APA becomes the operations layer."
      />

      <Section title="Snapshot">
        <div className="grid sm:grid-cols-3 lg:grid-cols-6 gap-5">
          {[
            { label: "Projects",  v: "8"   },
            { label: "Clients",   v: "3"   },
            { label: "Revenue",   v: "₹4.2L", accent: true },
            { label: "Tasks",     v: "47"  },
            { label: "Documents", v: "212" },
            { label: "Agents",    v: "10"  },
          ].map(s => (
            <div key={s.label}>
              <p className="text-[9px] uppercase tracking-[0.22em] text-muted-foreground">{s.label}</p>
              <p className={`mt-2 font-display text-[22px] ${s.accent ? "text-accent" : ""}`}>{s.v}</p>
            </div>
          ))}
        </div>
      </Section>

      <Section title="This week">
        <ul className="divide-y hairline">
          {[
            { who: "Research Agent", what: "Delivered market scan · 18 startups" },
            { who: "Communication Agent", what: "Drafted 4 client updates · awaiting approval" },
            { who: "Planner Agent", what: "Scheduled 3 client meetings next week" },
            { who: "Career Agent", what: "Updated resume with ATM Protocol metrics" },
          ].map((row, i) => (
            <li key={i} className="py-3 grid grid-cols-[180px_1fr] gap-4 text-[12.5px]">
              <span className="text-accent text-[10px] uppercase tracking-[0.22em]">{row.who}</span>
              <span>{row.what}</span>
            </li>
          ))}
        </ul>
      </Section>
    </Shell>
  );
}
