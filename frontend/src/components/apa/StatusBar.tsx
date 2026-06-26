import { useEnt } from "@/lib/apa/enterprise";
import { useApa } from "@/lib/apa/store";

export function StatusBar() {
  const ws = useEnt(s => s.workspaces.find(w => w.id === s.activeWorkspaceId)!);
  const devices = useApa(s => s.devices);
  const memory = useApa(s => s.memory);
  const outcomes = useApa(s => s.outcomes);
  const active = outcomes.filter(o => o.currentStage !== "complete").length;
  const connected = devices.filter(d => d.status !== "offline").length;

  return (
    <footer
      role="contentinfo"
      className="fixed bottom-0 left-0 right-0 z-30 border-t hairline bg-background/85 backdrop-blur"
    >
      <div className="mx-auto max-w-[1680px] flex items-center justify-between gap-6 px-6 py-1.5 text-[10px] font-mono uppercase tracking-[0.18em] text-muted-foreground">
        <div className="flex items-center gap-4">
          <Dot tone="success" /> backend
          <Dot tone="success" /> ws
          <span className="opacity-60">devices · {connected}/{devices.length}</span>
          <span className="opacity-60">knowledge · {memory.length}</span>
          <span className="opacity-60">active · {active}</span>
        </div>
        <div className="flex items-center gap-3">
          <span>workspace</span>
          <span className="text-accent">{ws.name}</span>
        </div>
      </div>
    </footer>
  );
}

function Dot({ tone }: { tone: "success" | "warn" | "error" }) {
  const c = tone === "success" ? "var(--color-success)" : tone === "warn" ? "var(--color-warn)" : "var(--color-destructive)";
  return <span className="inline-block h-1.5 w-1.5 rounded-full" style={{ background: c }} />;
}
