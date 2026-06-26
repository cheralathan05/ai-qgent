import { useState } from "react";
import { entStore, useEnt } from "@/lib/apa/enterprise";
import { Link } from "@tanstack/react-router";

export function TopBar() {
  const ws = useEnt(s => s.workspaces);
  const activeId = useEnt(s => s.activeWorkspaceId);
  const active = ws.find(w => w.id === activeId)!;
  const notifications = useEnt(s => s.notifications);
  const unread = notifications.filter(n => !n.read).length;

  const [wsOpen, setWsOpen] = useState(false);
  const [notifOpen, setNotifOpen] = useState(false);

  return (
    <div className="sticky top-0 z-30 border-b hairline bg-background/85 backdrop-blur">
      <div className="flex items-center justify-between px-6 py-2.5">
        <div className="flex items-center gap-3 relative">
          <button
            onClick={() => { setWsOpen(o => !o); setNotifOpen(false); }}
            className="flex items-center gap-2 text-[11px] uppercase tracking-[0.18em] text-muted-foreground hover:text-foreground"
            aria-haspopup="menu"
            aria-expanded={wsOpen}
          >
            <span className="h-1.5 w-1.5 rounded-full bg-accent" />
            <span className="text-foreground">{active.name}</span>
            <span className="opacity-60">workspace</span>
            <span className="text-accent">⌄</span>
          </button>
          {wsOpen && (
            <div className="absolute top-full left-0 mt-2 w-56 rounded-md border hairline-strong bg-background shadow-2xl py-1 z-40">
              {ws.map(w => (
                <button
                  key={w.id}
                  onClick={() => { entStore.set(s => ({ ...s, activeWorkspaceId: w.id })); setWsOpen(false); }}
                  className={[
                    "w-full text-left px-3 py-2 text-[12.5px] flex items-center justify-between hover:bg-surface/60",
                    w.id === activeId ? "text-foreground" : "text-muted-foreground"
                  ].join(" ")}
                >
                  <span>{w.name}</span>
                  <span className="text-[9px] uppercase tracking-wider opacity-60">{w.kind}</span>
                </button>
              ))}
              <div className="border-t hairline mt-1 pt-1">
                <Link to="/workspaces" onClick={() => setWsOpen(false)} className="block px-3 py-2 text-[11px] uppercase tracking-[0.18em] text-accent">Manage workspaces →</Link>
              </div>
            </div>
          )}
        </div>

        <div className="flex items-center gap-4">
          <kbd className="hidden md:inline font-mono text-[9px] text-muted-foreground border hairline rounded px-1.5 py-0.5">⌘K</kbd>
          <button
            onClick={() => entStore.set(s => ({ ...s, prefs: { ...s.prefs, copilotOpen: !s.prefs.copilotOpen } }))}
            className="text-[11px] uppercase tracking-[0.18em] text-muted-foreground hover:text-foreground"
            aria-label="Toggle Copilot"
          >Copilot <span className="opacity-60">⌘/</span></button>

          <div className="relative">
            <button
              onClick={() => { setNotifOpen(o => !o); setWsOpen(false); }}
              className="relative text-[11px] uppercase tracking-[0.18em] text-muted-foreground hover:text-foreground"
              aria-label={`Notifications, ${unread} unread`}
              aria-haspopup="menu"
            >
              Inbox
              {unread > 0 && (
                <span className="absolute -top-1 -right-3 h-1.5 w-1.5 rounded-full bg-accent apa-pulse" />
              )}
            </button>
            {notifOpen && (
              <div className="absolute top-full right-0 mt-2 w-[340px] rounded-md border hairline-strong bg-background shadow-2xl z-40">
                <div className="px-3 py-2 border-b hairline flex items-center justify-between">
                  <p className="text-[10px] uppercase tracking-[0.22em] text-muted-foreground">Notifications</p>
                  <Link to="/notifications" onClick={() => setNotifOpen(false)} className="text-[10px] uppercase tracking-[0.18em] text-accent">All →</Link>
                </div>
                <ul className="max-h-[60vh] overflow-y-auto">
                  {notifications.slice(0, 8).map(n => (
                    <li key={n.id} className="px-3 py-2 border-b hairline last:border-0">
                      <div className="flex items-center justify-between gap-2">
                        <p className="text-[12px] truncate">{n.title}</p>
                        <span className="font-mono text-[9px] uppercase text-muted-foreground">{n.category}</span>
                      </div>
                      {n.body && <p className="text-[11px] text-muted-foreground mt-0.5">{n.body}</p>}
                    </li>
                  ))}
                  {notifications.length === 0 && (
                    <li className="px-3 py-6 text-[11px] text-center text-muted-foreground">Inbox is quiet.</li>
                  )}
                </ul>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
