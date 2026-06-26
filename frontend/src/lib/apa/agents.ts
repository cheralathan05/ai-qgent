import type { Agent, AgentId } from "./types";

export const AGENTS: Record<AgentId, Agent> = {
  vision:        { id: "vision",        name: "Vision Agent",        role: "Reads screens, screenshots, documents" },
  memory:        { id: "memory",        name: "Memory Agent",        role: "Recalls, stores, and corrects facts" },
  planner:       { id: "planner",       name: "Planner Agent",       role: "Sequences steps and time blocks" },
  research:      { id: "research",      name: "Research Agent",      role: "Searches the web and your library" },
  device:        { id: "device",        name: "Device Agent",        role: "Talks to phone, laptop, browser, drive" },
  goal:          { id: "goal",          name: "Goal Agent",          role: "Connects every action to a north-star" },
  learning:      { id: "learning",      name: "Learning Agent",      role: "Builds study plans, notes, revisions" },
  communication: { id: "communication", name: "Communication Agent", role: "Drafts and sends messages" },
  automation:    { id: "automation",    name: "Automation Agent",    role: "Runs recurring background tasks" },
  security:      { id: "security",      name: "Security Agent",      role: "Reviews permissions and risk" },
};

export const AGENT_LIST = Object.values(AGENTS);
