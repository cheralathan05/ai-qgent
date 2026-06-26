import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { Shell, PageHeader, Section } from "@/components/apa/Shell";
import { useApa } from "@/lib/apa/store";
import { useEnt, logoutUser } from "@/lib/apa/enterprise";

export const Route = createFileRoute("/profile")({
  head: () => ({ meta: [{ title: "Profile — APA-OS" }] }),
  component: ProfilePage,
});

function ProfilePage() {
  const twin = useApa((s) => s.twin);
  const goals = useApa((s) => s.goals);
  const user = useEnt((s) => s.user);
  const navigate = useNavigate();

  function handleLogout() {
    logoutUser();
    navigate({ to: "/login" });
  }

  return (
    <Shell>
      <PageHeader
        eyebrow="You"
        title="Profile."
        lede="The version of you APA holds in memory. Preferences, patterns, north stars."
      />

      <Section title="Identity">
        <div className="grid sm:grid-cols-2 gap-5">
          <Field label="Name" value={user?.name ?? "Guest"} />
          <Field label="Email" value={user?.email ?? "Not signed in"} />
          <Field label="Role" value="Student · Founder" />
          <Field label="Joined" value="6 months ago" />
        </div>
        <div className="mt-6">
          <button
            onClick={handleLogout}
            className="rounded-xl border border-destructive/40 px-5 py-2.5 text-[11px] uppercase tracking-[0.22em] text-destructive hover:bg-destructive/10 transition-all"
          >
            Sign out
          </button>
        </div>
      </Section>

      <Section title="Patterns (from your Twin)">
        <ul className="space-y-2 text-[13px]">
          <li>— {twin.sleep}</li>
          <li>— {twin.focusWindow}</li>
          <li>— {twin.studyPeak}</li>
          <li>— {twin.style}</li>
        </ul>
      </Section>

      <Section title="North stars">
        <ul className="space-y-2">
          {goals.map((g) => (
            <li key={g.id} className="flex justify-between text-[12.5px]">
              <span>{g.title}</span>
              <span className="font-mono text-[10px] text-accent">{g.progress}%</span>
            </li>
          ))}
        </ul>
      </Section>
    </Shell>
  );
}

function Field({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p className="text-[9px] uppercase tracking-[0.22em] text-muted-foreground">{label}</p>
      <p className="mt-1 font-display text-[16px]">{value}</p>
    </div>
  );
}
