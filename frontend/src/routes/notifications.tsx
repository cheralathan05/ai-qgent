import { createFileRoute } from "@tanstack/react-router";
import { useState } from "react";
import { Shell, PageHeader, Section } from "@/components/apa/Shell";
import { useEnt } from "@/lib/apa/enterprise";
import type { NotificationCategory } from "@/lib/apa/enterprise";

export const Route = createFileRoute("/notifications")({
  head: () => ({ meta: [{ title: "Inbox — APA-OS" }] }),
  component: NotificationsPage,
});

const CATS: NotificationCategory[] = ["execution", "device", "knowledge", "workflow", "system", "approval"];

function NotificationsPage() {
  const all = useEnt(s => s.notifications);
  const [q, setQ] = useState("");
  const [cat, setCat] = useState<NotificationCategory | "all">("all");
  const items = all.filter(n =>
    (cat === "all" || n.category === cat) &&
    (!q || n.title.toLowerCase().includes(q.toLowerCase()) || n.body?.toLowerCase().includes(q.toLowerCase()))
  );
  return (
    <Shell>
      <PageHeader eyebrow="Inbox" title="Notification Center."
        lede="Every signal the system raised — categorised, searchable, never lost." />
      <Section>
        <div className="flex flex-wrap items-center gap-2 mb-5">
          <input value={q} onChange={e => setQ(e.target.value)} placeholder="Search…"
            className="bg-surface rounded-md px-3 py-1.5 text-[12px] border hairline focus:border-accent outline-none" />
          {(["all", ...CATS] as const).map(c => (
            <button key={c} onClick={() => setCat(c as any)}
              className={["px-2.5 py-1 rounded-md text-[10.5px] uppercase tracking-[0.18em] border hairline",
                cat === c ? "bg-accent text-accent-foreground border-transparent" : "text-muted-foreground hover:text-foreground"].join(" ")}>{c}</button>
          ))}
        </div>
        <ul className="border hairline rounded-md divide-y divide-[var(--color-border)]">
          {items.map(n => (
            <li key={n.id} className="px-4 py-3 flex items-start gap-4">
              <span className="font-mono text-[9px] uppercase tracking-wider text-accent w-20 shrink-0 pt-0.5">{n.category}</span>
              <div className="flex-1 min-w-0">
                <p className="text-[13px]">{n.title}</p>
                {n.body && <p className="text-[11.5px] text-muted-foreground mt-0.5">{n.body}</p>}
              </div>
              <span className="font-mono text-[10px] text-muted-foreground">{new Date(n.at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}</span>
            </li>
          ))}
          {items.length === 0 && (
            <li className="px-4 py-10 text-center text-[12px] text-muted-foreground italic">All quiet.</li>
          )}
        </ul>
      </Section>
    </Shell>
  );
}
