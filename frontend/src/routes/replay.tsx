import { createFileRoute } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { Shell, PageHeader, Section } from "@/components/apa/Shell";
import { useApa } from "@/lib/apa/store";

export const Route = createFileRoute("/replay")({
  head: () => ({ meta: [{ title: "Execution Replay — APA-OS V3" }] }),
  component: ReplayPage,
});

function ReplayPage() {
  const replay = useApa(s => s.replay);
  const [idx, setIdx] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [speed, setSpeed] = useState(1);

  useEffect(() => { setIdx(replay.length); }, [replay.length]);

  useEffect(() => {
    if (!playing) return;
    const interval = setInterval(() => {
      setIdx(i => (i >= replay.length ? (setPlaying(false), i) : i + 1));
    }, 600 / speed);
    return () => clearInterval(interval);
  }, [playing, replay.length, speed]);

  const shown = replay.slice(0, idx);

  return (
    <Shell>
      <PageHeader
        eyebrow="Hidden Layer 10"
        title="Execution Replay."
        lede="Every action the system takes is recorded as a scrubable timeline. There are no invisible decisions."
      />

      <Section title="Playback console" aside={
        <p className="font-mono text-[10px] uppercase tracking-wider text-muted-foreground">
          {idx} / {replay.length} steps
        </p>
      }>
        <div className="rounded-xl border hairline-strong bg-surface/40 p-5">
          <div className="flex items-center gap-3">
            <button
              onClick={() => setPlaying(p => !p)}
              disabled={replay.length === 0}
              className="rounded-md bg-accent text-accent-foreground px-4 py-1.5 text-[12px] disabled:opacity-40"
            >
              {playing ? "Pause" : "▶ Play"}
            </button>
            <button onClick={() => { setIdx(0); setPlaying(false); }} className="rounded-md border hairline px-3 py-1.5 text-[12px]">Restart</button>
            <button onClick={() => setIdx(replay.length)} className="rounded-md border hairline px-3 py-1.5 text-[12px]">Skip to end</button>
            <div className="flex gap-px ml-2 rounded overflow-hidden border hairline bg-[var(--color-border)]">
              {[0.5, 1, 2, 4].map(s => (
                <button key={s} onClick={() => setSpeed(s)}
                        className={`px-2 py-1 text-[10px] ${speed === s ? "bg-accent text-accent-foreground" : "bg-background text-muted-foreground"}`}>
                  {s}×
                </button>
              ))}
            </div>
          </div>
          <input
            type="range"
            min={0}
            max={replay.length}
            value={idx}
            onChange={e => setIdx(Number(e.target.value))}
            className="mt-4 w-full accent-[color:var(--color-accent)]"
          />
        </div>
      </Section>

      <Section title="Recorded actions">
        {shown.length === 0 ? (
          <p className="text-sm text-muted-foreground italic">No actions yet. Run an outcome from the Console.</p>
        ) : (
          <ol className="relative border-l hairline-strong pl-7 space-y-5 max-w-3xl">
            {shown.map(r => (
              <li key={r.id} className="relative apa-fade-up">
                <span className="absolute -left-[34px] top-1.5 h-2 w-2 rounded-full bg-accent" />
                <p className="font-mono text-[10px] uppercase tracking-[0.18em] text-muted-foreground">
                  {new Date(r.at).toLocaleTimeString()} {r.agent && `· ${r.agent}`}
                </p>
                <p className="mt-1 text-[14px]">{r.label}</p>
                <p className="text-[12px] text-muted-foreground">{r.detail}</p>
              </li>
            ))}
          </ol>
        )}
      </Section>
    </Shell>
  );
}
