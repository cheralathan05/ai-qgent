export type AgentId =
  | "vision" | "memory" | "planner" | "research" | "device"
  | "goal" | "learning" | "communication" | "automation" | "security";

export type AgentStatus =
  | "idle" | "queued" | "thinking" | "running" | "waiting"
  | "blocked" | "done" | "failed" | "skipped";

export interface Agent {
  id: AgentId;
  name: string;
  role: string;
}

export interface AgentRun {
  agentId: AgentId;
  status: AgentStatus;
  note?: string;
  ms?: number;
  confidence?: number;
}

export type StageKey =
  | "intent" | "agents" | "memory" | "world"
  | "predictions" | "plan" | "execution" | "complete";

export interface StageEvent {
  key: StageKey;
  startedAt: number;
  finishedAt?: number;
}

export interface KeyValue { label: string; value: string; tone?: "default" | "accent" | "warn" | "success"; }

export interface ExecutionLog { at: number; label: string; agent: AgentId; status: "ok" | "pending" | "warn"; }

export interface AgentMessage { from: AgentId; to?: AgentId; text: string; at: number; }

export interface NextAction { label: string; impact?: string; minutes?: number; }

export interface Outcome {
  id: string;
  text: string;
  createdAt: number;
  category: string;
  priority: "low" | "medium" | "high";
  duration: string;
  agents: AgentRun[];
  plan: PlanStep[];
  rationale: string;
  confidence: number;
  emergency: boolean;
  stages: StageEvent[];
  currentStage: StageKey;
  memoryRecall: KeyValue[];
  worldContext: KeyValue[];
  predictions: { label: string; value: number; delta?: number }[];
  executionLog: ExecutionLog[];
  conversation: AgentMessage[];
  nextActions: NextAction[];
  worldHighlights: string[]; // node ids
}

export interface PlanStep {
  id: string;
  title: string;
  detail: string;
  when: string;
  agent: AgentId;
  done?: boolean;
}

export interface Goal {
  id: string;
  title: string;
  horizon: string;
  pillars: string[];
  progress: number;
  createdAt: number;
}

export interface MemoryNote {
  id: string;
  kind: "person" | "preference" | "fact" | "correction" | "document";
  text: string;
  createdAt: number;
  confidence?: number;
}

export interface TimelineEvent {
  id: string;
  when: number;
  bucket: "past" | "today" | "tomorrow" | "week" | "month";
  title: string;
  source: string;
}

export interface WorldNode {
  id: string;
  label: string;
  kind: "self" | "person" | "place" | "project" | "deadline" | "goal" | "device" | "subject" | "app";
  meta?: Record<string, string>;
}

export interface WorldEdge { from: string; to: string; relation: string; weight?: number; }

export interface DeviceLink {
  id: string;
  name: string;
  kind: "phone" | "laptop" | "browser" | "cloud" | "email" | "drive";
  status: "connected" | "observed" | "offline" | "controlling";
  lastSync: number;
  battery?: number;
  capabilities?: string[];
}

export interface DeviceInfo {
  id: string;
  name: string;
  device_name?: string;
  model: string;
  manufacturer: string;
  android_version: string;
  battery: number;
  is_online: boolean;
  connection_type: string;
  serial?: string;
  screen_width?: number;
  screen_height?: number;
  last_seen: string | null;
  twin?: {
    readiness_score?: number;
    ai_ready?: boolean;
    health_score?: number;
    trust_score?: number;
    sync_state?: string;
  };
}

export interface ReplayStep {
  id: string;
  outcomeId: string;
  label: string;
  detail: string;
  at: number;
  agent?: AgentId;
}

export type AutonomyMode = "manual" | "assist" | "autonomous";
