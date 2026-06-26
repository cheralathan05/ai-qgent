import { useEffect, useState, useSyncExternalStore } from "react";
import type {
  Outcome, Goal, MemoryNote, TimelineEvent,
  WorldNode, WorldEdge, DeviceLink, ReplayStep, AutonomyMode,
} from "./types";

const KEY = "apa-os-v2:state:v3";

interface State {
  outcomes: Outcome[];
  goals: Goal[];
  memory: MemoryNote[];
  timeline: TimelineEvent[];
  world: { nodes: WorldNode[]; edges: WorldEdge[] };
  devices: DeviceLink[];
  replay: ReplayStep[];
  autonomy: AutonomyMode;
  focusedOutcomeId: string | null;
  twin: {
    sleep: string;
    focusWindow: string;
    studyPeak: string;
    style: string;
    learningSpeed: string;
    preferredApps: string[];
  };
}

const seed = (): State => ({
  outcomes: [],
  autonomy: "assist",
  focusedOutcomeId: null,
  goals: [
    {
      id: "g1",
      title: "Pass the semester with distinction",
      horizon: "this semester",
      pillars: ["Revision", "Assignments", "Mock tests", "Sleep hygiene"],
      progress: 42,
      createdAt: Date.now() - 1000 * 60 * 60 * 24 * 9,
    },
    {
      id: "g2",
      title: "Get placed at a top product company",
      horizon: "6 months",
      pillars: ["DSA", "System Design", "Resume", "Applications", "Mock interviews"],
      progress: 18,
      createdAt: Date.now() - 1000 * 60 * 60 * 24 * 21,
    },
  ],
  memory: [
    { id: "m1", kind: "person",     text: "Deepak — classmate, ATM Protocol project partner.", createdAt: Date.now() - 86400000 * 12, confidence: 96 },
    { id: "m2", kind: "preference", text: "Prefers study sessions between 8 PM and 10 PM.",    createdAt: Date.now() - 86400000 * 7,  confidence: 92 },
    { id: "m3", kind: "correction", text: "When user says 'Deepak', it is never Deepak Sharma from cohort B.", createdAt: Date.now() - 86400000 * 3, confidence: 99 },
    { id: "m4", kind: "document",   text: "ATM Protocol PDF — last opened ~ a month ago, lives in Drive › College › Sem 5.", createdAt: Date.now() - 86400000 * 30, confidence: 88 },
    { id: "m5", kind: "fact",       text: "Compilers exam scheduled in 8 days.", createdAt: Date.now() - 86400000 * 1, confidence: 100 },
  ],
  timeline: [
    { id: "t1", when: Date.now() - 86400000 * 4, bucket: "past",     title: "Submitted DBMS assignment 3", source: "automation" },
    { id: "t2", when: Date.now() - 86400000 * 2, bucket: "past",     title: "Note added — Operating Systems unit 4", source: "memory" },
    { id: "t3", when: Date.now(),                bucket: "today",    title: "Two pending tasks for Compilers revision", source: "planner" },
    { id: "t4", when: Date.now() + 86400000,     bucket: "tomorrow", title: "Compilers mock test, 7 PM", source: "calendar" },
    { id: "t5", when: Date.now() + 86400000 * 6, bucket: "week",     title: "Semester revision sprint", source: "goal" },
    { id: "t6", when: Date.now() + 86400000 * 21,bucket: "month",    title: "End-semester examinations", source: "auto" },
  ],
  world: {
    nodes: [
      { id: "self",     label: "You",            kind: "self" },
      { id: "college",  label: "College",        kind: "place" },
      { id: "deepak",   label: "Deepak",         kind: "person", meta: { role: "Classmate · ATM partner", importance: "87" } },
      { id: "exam",     label: "Sem 5 Exams",    kind: "deadline", meta: { date: "in 8 days" } },
      { id: "atm",      label: "ATM Protocol",   kind: "project" },
      { id: "placement",label: "Placement",      kind: "goal" },
      { id: "semester", label: "Pass Semester",  kind: "goal" },
      { id: "laptop",   label: "MacBook",        kind: "device" },
      { id: "phone",    label: "Phone",          kind: "device" },
      { id: "compiler", label: "Compilers",      kind: "subject" },
      { id: "dbms",     label: "DBMS",           kind: "subject" },
      { id: "whatsapp", label: "WhatsApp",       kind: "app" },
      { id: "drive",    label: "Drive",          kind: "app" },
    ],
    edges: [
      { from: "self", to: "college",   relation: "studies at", weight: 60 },
      { from: "self", to: "deepak",    relation: "collaborates with", weight: 95 },
      { from: "self", to: "exam",      relation: "preparing for", weight: 88 },
      { from: "self", to: "atm",       relation: "owns", weight: 70 },
      { from: "self", to: "placement", relation: "pursuing", weight: 80 },
      { from: "self", to: "semester",  relation: "pursuing", weight: 90 },
      { from: "self", to: "laptop",    relation: "uses", weight: 70 },
      { from: "self", to: "phone",     relation: "uses", weight: 85 },
      { from: "deepak", to: "atm",     relation: "co-owns", weight: 80 },
      { from: "exam", to: "compiler",  relation: "covers", weight: 90 },
      { from: "exam", to: "dbms",      relation: "covers", weight: 70 },
      { from: "phone", to: "whatsapp", relation: "runs", weight: 80 },
      { from: "atm",  to: "drive",     relation: "stored in", weight: 60 },
      { from: "deepak", to: "whatsapp", relation: "reachable via", weight: 90 },
      { from: "semester", to: "exam",  relation: "blocked by", weight: 95 },
    ],
  },
  devices: [
    { id: "d1", name: "MacBook Air",  kind: "laptop",  status: "connected", lastSync: Date.now() - 1000 * 60 * 4,  battery: 88, capabilities: ["Read screen", "Open apps", "Type", "Files"] },
    { id: "d2", name: "iPhone",       kind: "phone",   status: "connected", lastSync: Date.now() - 1000 * 60 * 12, battery: 72, capabilities: ["Open apps", "Tap", "Swipe", "Notifications", "WhatsApp", "Camera"] },
    { id: "d3", name: "Chrome",       kind: "browser", status: "observed",  lastSync: Date.now() - 1000 * 60 * 2,  capabilities: ["Read tabs", "Navigate", "Fill forms"] },
    { id: "d4", name: "Google Drive", kind: "drive",   status: "connected", lastSync: Date.now() - 1000 * 60 * 33, capabilities: ["Read files", "Search", "Share"] },
    { id: "d5", name: "Gmail",        kind: "email",   status: "observed",  lastSync: Date.now() - 1000 * 60 * 1,  capabilities: ["Read inbox", "Draft replies"] },
    { id: "d6", name: "iCloud",       kind: "cloud",   status: "offline",   lastSync: Date.now() - 1000 * 60 * 60 * 9 },
  ],
  replay: [],
  twin: {
    sleep: "Sleeps ~ 12:40 AM, wakes ~ 8:10 AM",
    focusWindow: "Deepest focus: 8 PM – 10 PM",
    studyPeak: "Study peak around 9 PM",
    style: "Concise, direct, prefers bullets over prose",
    learningSpeed: "Fast on theory, slower on derivations",
    preferredApps: ["Notion", "WhatsApp", "VS Code", "Drive"],
  },
});

let state: State =
  typeof window === "undefined"
    ? seed()
    : (() => {
        try {
          const raw = window.localStorage.getItem(KEY);
          if (!raw) return seed();
          const parsed = JSON.parse(raw) as State;
          return { ...seed(), ...parsed };
        } catch { return seed(); }
      })();

const listeners = new Set<() => void>();

function persist() {
  if (typeof window === "undefined") return;
  try { window.localStorage.setItem(KEY, JSON.stringify(state)); } catch {}
}

function emit() { listeners.forEach(l => l()); }

export const apaStore = {
  get: () => state,
  set: (updater: (s: State) => State) => {
    state = updater(state);
    persist();
    emit();
  },
  subscribe: (l: () => void) => {
    listeners.add(l);
    return () => listeners.delete(l);
  },
  reset: () => {
    state = seed();
    persist();
    emit();
  },
};

export function useApa<T>(selector: (s: State) => T): T {
  const [client, setClient] = useState(false);
  useEffect(() => setClient(true), []);
  const snap = useSyncExternalStore(
    apaStore.subscribe,
    () => selector(apaStore.get()),
    () => selector(seed()),
  );
  return client ? snap : selector(seed());
}

export type { State };
