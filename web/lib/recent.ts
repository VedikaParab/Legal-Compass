// Recent checks and checklist ticks, kept only in this browser (localStorage). Never sent to the server.
import type { Analysis } from "./types";

export type Recent = { id: string; at: string; title: string; law: string | null; sections: string[]; narrative: string; answers: Record<string, string> };
const KEY = "lc-recent";

export function hash(s: string): string {
  let h = 5381;
  for (let i = 0; i < s.length; i++) h = ((h << 5) + h + s.charCodeAt(i)) | 0;
  return (h >>> 0).toString(36);
}

export function loadRecent(): Recent[] {
  try { return JSON.parse(localStorage.getItem(KEY) || "[]") as Recent[]; } catch { return []; }
}

export function saveRecent(a: Analysis, narrative: string, answers: Record<string, string>): Recent[] {
  const id = hash(narrative.trim());
  const item: Recent = {
    id, at: new Date().toISOString(), narrative, answers,
    title: a.offences.map((o) => o.label).slice(0, 2).join(", ") || narrative.slice(0, 60),
    law: a.regime.law,
    sections: a.sections.slice(0, 3).map((s) => (a.primary_code === "BNS" && s.bns[0] ? s.bns[0].provision : `IPC ${s.ipc}`)),
  };
  const list = [item, ...loadRecent().filter((r) => r.id !== id)].slice(0, 6);
  try { localStorage.setItem(KEY, JSON.stringify(list)); } catch { /* storage blocked */ }
  return list;
}

export function clearRecent() {
  try { localStorage.removeItem(KEY); } catch { /* storage blocked */ }
}

export function loadTicks(key: string): Record<string, boolean> {
  try { return JSON.parse(localStorage.getItem(`lc-check-${key}`) || "{}"); } catch { return {}; }
}

export function saveTicks(key: string, v: Record<string, boolean>) {
  try { localStorage.setItem(`lc-check-${key}`, JSON.stringify(v)); } catch { /* storage blocked */ }
}
