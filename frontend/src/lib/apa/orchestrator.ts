import { apaStore } from "./store";
import type {
  AgentId, AgentRun, Outcome, PlanStep, ReplayStep,
  StageKey, KeyValue, ExecutionLog, AgentMessage, NextAction,
} from "./types";

const uid = () => Math.random().toString(36).slice(2, 10);

interface Match {
  category: string;
  priority: "low" | "medium" | "high";
  duration: string;
  agents: AgentId[];
  steps: Omit<PlanStep, "id" | "done">[];
  rationale: string;
  emergency: boolean;
  memoryRecall: KeyValue[];
  worldContext: KeyValue[];
  worldHighlights: string[];
  predictions: { label: string; value: number; delta?: number }[];
  conversationSeed: { from: AgentId; to?: AgentId; text: string }[];
  executionSeed: { label: string; agent: AgentId }[];
  nextActions: NextAction[];
}

function classify(text: string): Match {
  const t = text.toLowerCase();
  const emergency = /(tomorrow|tonight|in an hour|asap|urgent|by morning)/.test(t);

  if (/(exam|revis|semester|prepar|study|test|tomorrow)/.test(t)) {
    return {
      category: "Education",
      priority: "high",
      duration: "≈ 3 hours",
      emergency,
      agents: ["goal", "memory", "learning", "planner", "automation", "communication"],
      rationale:
        "Outcome maps to an academic objective. Goal Agent anchors it to 'Pass the semester'. Learning Agent rebuilds a revision plan from notes. Planner Agent slots it into your 8–10 PM focus window. Memory Agent recalls weak topics. Automation Agent watches the portal. Communication Agent prepares to ping your study group.",
      steps: [
        { title: "Revision plan — 5 days", detail: "Auto-built from notes and past assignments. Weighted by predicted weak topics.", when: "Starting tonight", agent: "learning" },
        { title: "Block focus time",       detail: "8 PM – 10 PM held on calendar. Notifications muted. Phone in focus mode.", when: "Today",           agent: "planner" },
        { title: "Pull notes & PDFs",      detail: "ATM Protocol, Compilers Unit 3-5, OS Unit 4. Indexed and summarised.",        when: "Now",             agent: "memory" },
        { title: "Watch portal",           detail: "College website + email monitored for surprise announcements.",                when: "Background",       agent: "automation" },
        { title: "Prep your group",        detail: "Draft a short check-in message to Deepak for tomorrow 7 PM mock test.",         when: "Drafted, awaits send", agent: "communication" },
        { title: "Daily readiness ping",   detail: "Every morning at 8:30 AM with what to revise and your readiness %.",            when: "Recurring",        agent: "goal" },
      ],
      memoryRecall: [
        { label: "Exam",          value: "Compiler Design" },
        { label: "Date",          value: "Tomorrow · 09:00 AM", tone: "warn" },
        { label: "Studied",       value: "Unit 1, Unit 2" },
        { label: "Weak area",     value: "Unit 4 — Code generation", tone: "warn" },
        { label: "Study partner", value: "Deepak" },
        { label: "Relevant docs", value: "7 documents found" },
      ],
      worldContext: [
        { label: "09:00",    value: "Compiler Exam", tone: "warn" },
        { label: "14:00",    value: "Lab Session" },
        { label: "Free",     value: "19:00 – 23:00", tone: "success" },
      ],
      worldHighlights: ["self", "exam", "compiler", "deepak", "semester"],
      predictions: [
        { label: "Exam readiness",    value: 74, delta: 18 },
        { label: "Placement",         value: 61 },
        { label: "Burnout risk",      value: 22 },
        { label: "Confidence if studied tonight", value: 92, delta: 18 },
      ],
      conversationSeed: [
        { from: "goal",     text: "Goal received: Prepare for tomorrow." },
        { from: "goal",     to: "memory",  text: "Need: exam schedule, weak topics, notes." },
        { from: "memory",   to: "goal",    text: "Compiler exam tomorrow 9 AM. Weak: Unit 4. 7 PDFs available." },
        { from: "goal",     to: "planner", text: "Build a 3-hour revision plan into the 8–10 PM focus window." },
        { from: "planner",  to: "learning",text: "Generate flashcards + quiz from Unit 4." },
        { from: "learning", text: "26 flashcards drafted. Quiz of 12 questions ready." },
        { from: "automation", text: "Calendar slot blocked. Phone focus mode armed." },
        { from: "communication", text: "Drafted check-in to Deepak — awaits your tap." },
      ],
      executionSeed: [
        { label: "Retrieved exam schedule",     agent: "memory" },
        { label: "Retrieved notes (7 PDFs)",    agent: "memory" },
        { label: "Built revision plan",         agent: "planner" },
        { label: "Generated 26 flashcards",     agent: "learning" },
        { label: "Generated 12-question quiz",  agent: "learning" },
        { label: "Calendar session added 8 PM", agent: "automation" },
        { label: "Portal watcher armed",        agent: "automation" },
        { label: "Drafted message to Deepak",   agent: "communication" },
      ],
      nextActions: [
        { label: "Start revision now", impact: "+3% goal", minutes: 45 },
        { label: "Take 12-question quiz", impact: "+5%", minutes: 18 },
        { label: "Open Compilers Unit 4 notes", minutes: 2 },
        { label: "Send draft to Deepak" },
        { label: "Generate one-page summary", minutes: 4 },
      ],
    };
  }

  if (/(open|launch|instagram|whatsapp|chrome|phone|gallery|app|device)/.test(t)) {
    const app = /instagram/.test(t) ? "Instagram"
      : /whatsapp/.test(t) ? "WhatsApp"
      : /chrome/.test(t) ? "Chrome"
      : /gallery/.test(t) ? "Gallery"
      : "the requested app";
    return {
      category: "Device control",
      priority: "medium",
      duration: "≈ 6 seconds",
      emergency: false,
      agents: ["planner", "device", "vision", "security"],
      rationale:
        "Device control outcome. Planner authorises, Device Agent wakes the phone, Vision Agent confirms the on-screen target, Security verifies permissions before the tap.",
      steps: [
        { title: "Wake device",      detail: "iPhone unlocked via paired session.",      when: "Now", agent: "device" },
        { title: `Locate ${app}`,     detail: "Vision Agent finds the app icon on screen.", when: "Now", agent: "vision" },
        { title: "Tap & verify",      detail: `${app} launched. Verified screen.`,         when: "Now", agent: "device" },
        { title: "Permission check",  detail: "No new permissions required.",              when: "Now", agent: "security" },
      ],
      memoryRecall: [
        { label: "App",           value: app },
        { label: "Last used",     value: "2 hours ago" },
        { label: "Device",        value: "iPhone 15" },
        { label: "Preference",    value: "Launch directly to feed" },
      ],
      worldContext: [
        { label: "Device", value: "iPhone · Connected", tone: "success" },
        { label: "Battery", value: "72%" },
        { label: "Latency", value: "220ms" },
      ],
      worldHighlights: ["self", "phone", "whatsapp"],
      predictions: [
        { label: "Success probability", value: 99 },
        { label: "Avg launch time",     value: 5 },
      ],
      conversationSeed: [
        { from: "planner", text: `Goal: open ${app}.` },
        { from: "planner", to: "device", text: "Wake iPhone." },
        { from: "device", to: "vision", text: "Screen ready. Find target." },
        { from: "vision", text: `${app} icon detected at (152, 624). Confidence 0.97.` },
        { from: "security", text: "No new permission required." },
        { from: "device", text: "Tap dispatched. Verifying…" },
        { from: "vision", text: `${app} home screen confirmed.` },
      ],
      executionSeed: [
        { label: "Detect device",    agent: "device" },
        { label: "Wake device",      agent: "device" },
        { label: `Locate ${app}`,    agent: "vision" },
        { label: `Launch ${app}`,    agent: "device" },
        { label: "Verify open",      agent: "vision" },
      ],
      nextActions: [
        { label: "Open profile" },
        { label: "Search…" },
        { label: "Close app" },
      ],
    };
  }

  if (/(send|message|whatsapp|email|ping|reply|attendance|screenshot)/.test(t)) {
    return {
      category: "Communication",
      priority: "medium",
      duration: "≈ 12 seconds",
      emergency,
      agents: ["memory", "vision", "device", "communication", "security"],
      rationale:
        "Communication outcome. Memory disambiguates the contact, Vision pulls the document, Device opens the right app, Communication composes the message, Security verifies the recipient.",
      steps: [
        { title: "Resolve contact",   detail: "'Deepak' → ATM Protocol partner, not Deepak Sharma from cohort B.", when: "Now", agent: "memory" },
        { title: "Find attachment",   detail: "Latest screenshot / ATM PDF located in Drive › College › Sem 5.", when: "Now", agent: "vision" },
        { title: "Open channel",      detail: "WhatsApp opened to correct thread.",                       when: "Now", agent: "device" },
        { title: "Compose & confirm", detail: "Short, your voice. Awaiting your one-tap confirm before sending.", when: "Now", agent: "communication" },
        { title: "Permission check",  detail: "No new permissions needed. No PII in payload.",                    when: "Now", agent: "security" },
      ],
      memoryRecall: [
        { label: "Contact",   value: "Deepak (ATM partner)" },
        { label: "Channel",   value: "WhatsApp" },
        { label: "File",      value: "Screenshot · 12 mins ago" },
        { label: "Tone",      value: "Concise, friendly" },
      ],
      worldContext: [
        { label: "Phone",    value: "Connected", tone: "success" },
        { label: "WhatsApp", value: "Ready" },
        { label: "Drive",    value: "Indexed" },
      ],
      worldHighlights: ["self", "deepak", "whatsapp", "phone", "drive"],
      predictions: [
        { label: "Delivery probability", value: 98 },
        { label: "Reply within 30 min",  value: 81 },
      ],
      conversationSeed: [
        { from: "memory", text: "Contact resolved → Deepak (ATM partner)." },
        { from: "vision", text: "Found screenshot in Photos · today 09:42." },
        { from: "device", text: "WhatsApp opened to thread." },
        { from: "communication", text: "Message drafted." },
        { from: "security", text: "Recipient verified. Awaiting confirmation." },
      ],
      executionSeed: [
        { label: "Resolved Deepak",         agent: "memory" },
        { label: "Located screenshot",      agent: "vision" },
        { label: "Opened WhatsApp",         agent: "device" },
        { label: "Attached file",           agent: "device" },
        { label: "Drafted message",         agent: "communication" },
        { label: "Awaiting your confirm",   agent: "security" },
      ],
      nextActions: [
        { label: "Send now" },
        { label: "Edit draft" },
        { label: "Add another file" },
      ],
    };
  }

  if (/(place|job|intern|interview|resume|career|semester|pass)/.test(t)) {
    return {
      category: "Career / Goal",
      priority: "high",
      duration: "Long-horizon",
      emergency: false,
      agents: ["goal", "memory", "learning", "research", "planner", "communication"],
      rationale:
        "Long-horizon goal. Goal Agent maintains the north-star and connects every smaller action to it.",
      steps: [
        { title: "Refresh placement plan", detail: "Skills → Projects → Resume → Applications → Interviews → Offer.", when: "Today", agent: "goal" },
        { title: "Next learning sprint",   detail: "DSA + System Design, 1 hour daily in your focus window.",        when: "Starting tonight", agent: "learning" },
        { title: "Company shortlist",      detail: "12 product companies matching your stack and CGPA.",             when: "Today", agent: "research" },
        { title: "Resume update",          detail: "ATM Protocol added with metrics. Awaiting your one-tap approve.",when: "Drafted", agent: "communication" },
        { title: "Weekly review",          detail: "Fridays 9 PM — what advanced, what slipped, what's next.",       when: "Recurring", agent: "planner" },
      ],
      memoryRecall: [
        { label: "Goal",        value: "Pass semester / Placement" },
        { label: "Strength",    value: "Theory · Projects" },
        { label: "Weakness",    value: "Derivations · System Design" },
        { label: "CGPA",        value: "8.2" },
      ],
      worldContext: [
        { label: "Semester",  value: "42% complete", tone: "warn" },
        { label: "Placement", value: "18% complete" },
        { label: "Time left", value: "21 days to finals" },
      ],
      worldHighlights: ["self", "semester", "placement", "exam"],
      predictions: [
        { label: "Goal probability", value: 47, delta: 5 },
        { label: "If +1h daily",     value: 69, delta: 22 },
        { label: "If +mock weekly",  value: 84, delta: 37 },
        { label: "If no action",     value: 31, delta: -16 },
      ],
      conversationSeed: [
        { from: "goal",     text: "North-star anchored: Pass semester with distinction." },
        { from: "memory",   text: "Pulled CGPA, strengths, weaknesses, exam dates." },
        { from: "learning", text: "Sprint plan generated. Compiler Unit 4 first." },
        { from: "research", text: "12 companies shortlisted." },
        { from: "planner",  text: "Weekly review scheduled. Daily pings armed." },
      ],
      executionSeed: [
        { label: "Goal locked",              agent: "goal" },
        { label: "Sprint built",             agent: "learning" },
        { label: "Shortlist generated",      agent: "research" },
        { label: "Resume updated (draft)",   agent: "communication" },
        { label: "Weekly review scheduled",  agent: "planner" },
      ],
      nextActions: [
        { label: "Start Compilers Unit 4", impact: "+3%", minutes: 45 },
        { label: "Approve resume draft", impact: "+2%" },
        { label: "Review shortlist" },
      ],
    };
  }

  return {
    category: "General",
    priority: "medium",
    duration: "≈ 30 minutes",
    emergency,
    agents: ["goal", "memory", "planner", "research"],
    rationale:
      "No single pattern dominated. Activated the core quartet — Goal frames the outcome, Memory grounds it, Planner sequences it, Research fills the gaps.",
    steps: [
      { title: "Frame the outcome",  detail: "Restated as a connected sub-goal under your active north-stars.", when: "Now",   agent: "goal" },
      { title: "Ground in memory",   detail: "Pulled relevant people, projects, and past decisions.",            when: "Now",   agent: "memory" },
      { title: "First three actions",detail: "Smallest viable next steps, sequenced for today.",                 when: "Today", agent: "planner" },
      { title: "Open questions",     detail: "Two things worth researching before we go further.",               when: "Today", agent: "research" },
    ],
    memoryRecall: [
      { label: "Active goals", value: "2" },
      { label: "Free time",    value: "tonight 8–11 PM" },
    ],
    worldContext: [
      { label: "Now",       value: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }) },
      { label: "Devices",   value: "5 online", tone: "success" },
    ],
    worldHighlights: ["self"],
    predictions: [
      { label: "Outcome confidence", value: 78 },
    ],
    conversationSeed: [
      { from: "goal",    text: "Framing this as a sub-goal of your active north-stars." },
      { from: "memory",  text: "Grounded with related people, files, and decisions." },
      { from: "planner", text: "Three smallest next steps queued." },
    ],
    executionSeed: [
      { label: "Outcome framed",         agent: "goal" },
      { label: "Memory grounded",        agent: "memory" },
      { label: "Plan drafted",           agent: "planner" },
    ],
    nextActions: [
      { label: "Show plan" },
      { label: "Start first step" },
    ],
  };
}

const STAGES: StageKey[] = ["intent", "agents", "memory", "world", "predictions", "plan", "execution", "complete"];

export async function runOutcome(text: string): Promise<string> {
  const match = classify(text);
  const id = uid();
  const now = Date.now();

  const agentRuns: AgentRun[] = match.agents.map(a => ({ agentId: a, status: "queued" }));
  const plan: PlanStep[] = match.steps.map(s => ({ ...s, id: uid(), done: false }));
  const confidence = Math.max(58, Math.min(99, 78 + Math.round(Math.random() * 18)));

  const outcome: Outcome = {
    id,
    text,
    createdAt: now,
    category: match.category,
    priority: match.priority,
    duration: match.duration,
    agents: agentRuns,
    plan,
    rationale: match.rationale,
    confidence,
    emergency: match.emergency,
    stages: [{ key: "intent", startedAt: now }],
    currentStage: "intent",
    memoryRecall: [],
    worldContext: [],
    predictions: [],
    executionLog: [],
    conversation: [],
    nextActions: match.nextActions,
    worldHighlights: match.worldHighlights,
  };

  apaStore.set(s => ({
    ...s,
    focusedOutcomeId: id,
    outcomes: [outcome, ...s.outcomes].slice(0, 25),
    timeline: [
      { id: uid(), when: now, bucket: "today" as const, title: `Outcome: ${text}`, source: "user" },
      ...s.timeline,
    ].slice(0, 80),
    replay: [
      ...match.executionSeed.map<ReplayStep>((e, i) => ({
        id: uid(), outcomeId: id, label: e.label, detail: `via ${e.agent}`, agent: e.agent, at: now + i * 220,
      })),
      ...s.replay,
    ].slice(0, 400),
  }));

  function patchOutcome(fn: (o: Outcome) => Outcome) {
    apaStore.set(s => ({
      ...s,
      outcomes: s.outcomes.map(o => o.id === id ? fn(o) : o),
    }));
  }

  function advanceStage(key: StageKey) {
    patchOutcome(o => ({
      ...o,
      currentStage: key,
      stages: [...o.stages.map(st => st.finishedAt ? st : { ...st, finishedAt: Date.now() }),
               { key, startedAt: Date.now() }],
    }));
  }

  // Stage: agents queueing
  await wait(300);
  advanceStage("agents");
  for (let i = 0; i < agentRuns.length; i++) {
    await wait(140 + Math.random() * 120);
    patchOutcome(o => ({
      ...o,
      agents: o.agents.map((a, idx) => idx === i ? { ...a, status: "thinking" } : a),
    }));
  }

  // Stage: memory recall stream
  await wait(280);
  advanceStage("memory");
  for (const item of match.memoryRecall) {
    await wait(160);
    patchOutcome(o => ({ ...o, memoryRecall: [...o.memoryRecall, item] }));
  }

  // Stage: world model
  await wait(220);
  advanceStage("world");
  for (const item of match.worldContext) {
    await wait(140);
    patchOutcome(o => ({ ...o, worldContext: [...o.worldContext, item] }));
  }

  // Stage: predictions
  await wait(220);
  advanceStage("predictions");
  for (const p of match.predictions) {
    await wait(160);
    patchOutcome(o => ({ ...o, predictions: [...o.predictions, p] }));
  }

  // Stage: plan generation — flip agents to running, stream conversation
  await wait(260);
  advanceStage("plan");
  for (const msg of match.conversationSeed) {
    await wait(220 + Math.random() * 180);
    const conv: AgentMessage = { ...msg, at: Date.now() };
    patchOutcome(o => ({ ...o, conversation: [...o.conversation, conv] }));
  }

  // Stage: execution — stream execution log + flip agents done
  await wait(260);
  advanceStage("execution");
  for (let i = 0; i < match.executionSeed.length; i++) {
    await wait(260 + Math.random() * 200);
    const e = match.executionSeed[i];
    const log: ExecutionLog = { at: Date.now(), label: e.label, agent: e.agent, status: "ok" };
    patchOutcome(o => ({
      ...o,
      executionLog: [...o.executionLog, log],
      agents: o.agents.map(a => a.agentId === e.agent
        ? { ...a, status: "running" } : a),
    }));
  }

  // settle agents to done
  for (let i = 0; i < agentRuns.length; i++) {
    await wait(120);
    patchOutcome(o => ({
      ...o,
      agents: o.agents.map((a, idx) => idx === i
        ? { ...a, status: "done", ms: 420 + Math.round(Math.random() * 600),
            confidence: 80 + Math.round(Math.random() * 18) }
        : a),
    }));
  }

  // complete
  await wait(180);
  advanceStage("complete");

  return id;
}

function wait(ms: number) { return new Promise(r => setTimeout(r, ms)); }

export const STAGE_LIST = STAGES;
export const STAGE_LABEL: Record<StageKey, string> = {
  intent:      "Intent capture",
  agents:      "Agent activation",
  memory:      "Memory recall",
  world:       "World model",
  predictions: "Predictions",
  plan:        "Plan generation",
  execution:   "Live execution",
  complete:    "Completed",
};
