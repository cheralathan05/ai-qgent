import { apaStore } from "./store";

export type NotificationCategory =
  | "execution" | "device" | "knowledge" | "workflow" | "system" | "approval";

export interface AppNotification {
  id: string;
  at: number;
  category: NotificationCategory;
  title: string;
  body?: string;
  read?: boolean;
  level?: "info" | "warn" | "error" | "success";
}

export type ActivityKind =
  | "command" | "device" | "knowledge" | "file" | "workflow"
  | "approval" | "notification" | "error" | "user" | "execution";

export interface ActivityEvent {
  id: string;
  at: number;
  kind: ActivityKind;
  title: string;
  source?: string;
  workspaceId?: string;
}

export interface ErrorEvent {
  id: string;
  at: number;
  area: "api" | "device" | "workflow" | "knowledge" | "websocket";
  title: string;
  recovery?: string;
  resolved?: boolean;
}

export interface Workspace {
  id: string;
  name: string;
  kind: "personal" | "career" | "study" | "startup" | "custom";
  accent?: string;
}

export interface FeatureFlags {
  knowledge: boolean;
  voice: boolean;
  mobileAgent: boolean;
  analytics: boolean;
  experimental: boolean;
}

export interface Personalization {
  highContrast: boolean;
  reducedMotion: boolean;
  pinnedActions: string[];
  pinnedDevices: string[];
  copilotOpen: boolean;
}

export interface UserProfile {
  id: string;
  full_name: string;
  email: string;
  email_verified: boolean;
  status: string;
  last_login: string | null;
  created_at: string;
  accessToken: string;
  refreshToken: string;
  session_id?: string;
}

export interface EnterpriseState {
  authenticated: boolean;
  user: UserProfile | null;
  workspaces: Workspace[];
  activeWorkspaceId: string;
  notifications: AppNotification[];
  activity: ActivityEvent[];
  errors: ErrorEvent[];
  flags: FeatureFlags;
  prefs: Personalization;
  onboardingComplete: boolean;
}

const ENT_KEY = "apa-os:enterprise:v1";
const TOKEN_KEY = "apa-os:tokens";

const seedEnt = (): EnterpriseState => ({
  authenticated: false,
  user: null,
  workspaces: [
    { id: "w-personal", name: "Personal", kind: "personal" },
    { id: "w-study",    name: "Study",    kind: "study"    },
    { id: "w-career",   name: "Career",   kind: "career"   },
  ],
  activeWorkspaceId: "w-personal",
  notifications: [
    { id: "n1", at: Date.now() - 1000*60*4,  category: "execution", level: "success", title: "Outcome completed", body: "Tomorrow prep · 8 stages." },
    { id: "n2", at: Date.now() - 1000*60*22, category: "device",    level: "info",    title: "iPhone reconnected", body: "WebSocket re-established." },
    { id: "n3", at: Date.now() - 1000*60*55, category: "approval",  level: "warn",    title: "Approval needed",   body: "Send screenshot to Deepak?" },
    { id: "n4", at: Date.now() - 1000*60*90, category: "knowledge", level: "info",    title: "Drive re-indexed",  body: "412 docs · 4 new." },
  ],
  activity: [
    { id: "a1", at: Date.now() - 1000*60*1,  kind: "command",      title: "⌘K opened" },
    { id: "a2", at: Date.now() - 1000*60*3,  kind: "execution",    title: "Planner agent finished plan", source: "planner" },
    { id: "a3", at: Date.now() - 1000*60*6,  kind: "device",       title: "Phone screen observed", source: "iPhone" },
    { id: "a4", at: Date.now() - 1000*60*9,  kind: "knowledge",    title: "Searched: ATM Protocol notes", source: "drive" },
    { id: "a5", at: Date.now() - 1000*60*14, kind: "approval",     title: "User approved screenshot share" },
    { id: "a6", at: Date.now() - 1000*60*30, kind: "workflow",     title: "Workflow run: morning brief" },
    { id: "a7", at: Date.now() - 1000*60*55, kind: "file",         title: "Opened: Compiler_Unit4.pdf" },
    { id: "a8", at: Date.now() - 1000*60*80, kind: "notification", title: "Reminder dispatched" },
  ],
  errors: [
    { id: "e1", at: Date.now() - 1000*60*120, area: "websocket", title: "Brief disconnect from iPhone bridge", recovery: "Auto-reconnected in 3s", resolved: true },
    { id: "e2", at: Date.now() - 1000*60*60*5, area: "knowledge", title: "Indexer rate-limited on Drive", recovery: "Retried after 60s · ok" , resolved: true},
  ],
  flags: { knowledge: true, voice: true, mobileAgent: true, analytics: false, experimental: false },
  prefs: { highContrast: false, reducedMotion: false, pinnedActions: ["Help me prepare for tomorrow", "Find my ATM Protocol notes"], pinnedDevices: ["d2"], copilotOpen: false },
  onboardingComplete: false,
});

let ent: EnterpriseState =
  typeof window === "undefined"
    ? seedEnt()
    : (() => {
        try {
          const raw = window.localStorage.getItem(ENT_KEY);
          if (!raw) return seedEnt();
          return { ...seedEnt(), ...JSON.parse(raw) };
        } catch { return seedEnt(); }
      })();

const listeners = new Set<() => void>();

function persist() {
  if (typeof window === "undefined") return;
  try { window.localStorage.setItem(ENT_KEY, JSON.stringify(ent)); } catch {}
}

export const entStore = {
  get: () => ent,
  set(u: (s: EnterpriseState) => EnterpriseState) {
    ent = u(ent);
    persist();
    listeners.forEach(l => l());
  },
  subscribe(l: () => void) { listeners.add(l); return () => listeners.delete(l); },
  reset() { ent = seedEnt(); persist(); listeners.forEach(l => l()); },
};

export function pushActivity(e: Omit<ActivityEvent, "id" | "at">) {
  entStore.set(s => ({
    ...s,
    activity: [{ id: crypto.randomUUID(), at: Date.now(), ...e }, ...s.activity].slice(0, 200),
  }));
}
export function pushNotification(n: Omit<AppNotification, "id" | "at">) {
  entStore.set(s => ({
    ...s,
    notifications: [{ id: crypto.randomUUID(), at: Date.now(), ...n }, ...s.notifications].slice(0, 200),
  }));
}
export function pushError(e: Omit<ErrorEvent, "id" | "at">) {
  entStore.set(s => ({
    ...s,
    errors: [{ id: crypto.randomUUID(), at: Date.now(), ...e }, ...s.errors].slice(0, 100),
  }));
}

export function loginUser(user: UserProfile) {
  localStorage.setItem('accessToken', user.accessToken);
  localStorage.setItem('refreshToken', user.refreshToken);
  localStorage.setItem('user', JSON.stringify(user));
  if (user.session_id) {
    localStorage.setItem('session_id', user.session_id);
  }
  entStore.set(s => ({ ...s, authenticated: true, user }));
}

export function logoutUser() {
  // Call backend to revoke session (fire-and-forget)
  const sessionId = localStorage.getItem('session_id');
  if (sessionId) {
    fetch('/api/auth/logout', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ session_id: sessionId }),
    }).catch(() => {});
  }

  // Clear all auth tokens
  localStorage.removeItem('accessToken');
  localStorage.removeItem('refreshToken');
  localStorage.removeItem('user');
  localStorage.removeItem('session_id');

  // Clear all pairing/device/WebSocket state
  localStorage.removeItem('apa-os:device-pairing');
  localStorage.removeItem('pairing_workflow_id');
  localStorage.removeItem('pairing_serial');
  localStorage.removeItem('pairing_device_id');
  localStorage.removeItem('pairing_step');
  localStorage.removeItem('pairing_trusted');
  localStorage.removeItem('device_connected');
  localStorage.removeItem('device_id');
  localStorage.removeItem('pairing_ws');

  // Clear React Query cache marker
  localStorage.removeItem('apa-os:query-cache');

  // Reset enterprise state
  entStore.set(s => ({ ...s, authenticated: false, user: null, onboardingComplete: false }));
}

export function getStoredUser(): UserProfile | null {
  try {
    const raw = localStorage.getItem('user');
    if (!raw) return null;
    return JSON.parse(raw) as UserProfile;
  } catch {
    return null;
  }
}

export function hasTokens(): boolean {
  return !!(localStorage.getItem('accessToken') && localStorage.getItem('refreshToken'));
}

import { useEffect, useState, useSyncExternalStore } from "react";
export function useEnt<T>(sel: (s: EnterpriseState) => T): T {
  const [c, setC] = useState(false);
  useEffect(() => setC(true), []);
  const snap = useSyncExternalStore(
    entStore.subscribe,
    () => sel(entStore.get()),
    () => sel(seedEnt()),
  );
  return c ? snap : sel(seedEnt());
}

export const __wired = !!apaStore;
