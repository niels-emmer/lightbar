export interface Act {
  pattern: string;
  duration_sec: number;
  [key: string]: unknown;
}

export interface Experiment {
  id: string;
  theme: string;
  inspiration: string;
  description: string;
  duration_minutes: number;
  acts: Act[];
  created_at: string;
  prompted_by: string | null;
}

export interface EngineStatus {
  running: boolean;
  light_on: boolean;
  device_online: boolean;
  current_experiment: Experiment | null;
  current_step_index: number;
  current_hue: number;
  current_saturation: number;
  current_value: number;
  experiment_started_at: string | null;
  next_experiment_in_seconds: number | null;
}

export interface LogEntry {
  timestamp: string;
  level: "info" | "ai" | "device" | "error" | "user";
  message: string;
  data: Record<string, unknown> | null;
}

export async function fetchStatus(): Promise<EngineStatus> {
  const r = await fetch("/api/status");
  if (!r.ok) throw new Error(`Status ${r.status}`);
  return r.json();
}

export async function fetchExperiments(): Promise<Experiment[]> {
  const r = await fetch("/api/experiments");
  if (!r.ok) throw new Error(`Status ${r.status}`);
  return r.json();
}

export async function postPrompt(prompt: string): Promise<void> {
  const r = await fetch("/api/prompt", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ prompt }),
  });
  if (!r.ok) throw new Error(`Status ${r.status}`);
}

export async function setPower(on: boolean): Promise<void> {
  const r = await fetch("/api/power", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ on }),
  });
  if (!r.ok) throw new Error(`Status ${r.status}`);
}

export async function skipExperiment(): Promise<void> {
  const r = await fetch("/api/skip", { method: "POST" });
  if (!r.ok) throw new Error(`Status ${r.status}`);
}

/** Returns an EventSource connected to /api/stream */
export function createEventSource(): EventSource {
  return new EventSource("/api/stream");
}
