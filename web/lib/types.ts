export type Question = {
  id: string;
  text: string;
  kind: "choice" | "date" | "text";
  options: string[];
  why: string;
  required: boolean;
  option_labels?: string[];
};

export type BnsTarget = { provision: string; heading?: string | null };

export type Section = {
  ipc: string;
  ipc_heading: string;
  bns: BnsTarget[];
  status: string;
  mapping_explained: string;
  change?: string | null;
  change_explained: string;
  notes: string[];
  row_ids: string[];
  source?: { document?: string | null; page?: string | null } | null;
  offence: string;
  basis: string;
  evidence: string[];
  confidence: number;
};

export type Regime = { decision: string; law: string | null; reason?: string; basis?: string[] };

export type Analysis = {
  ready: boolean;
  questions: Question[];
  required_missing: string[];
  facts: Record<string, unknown>;
  answers: Record<string, string>;
  answer_labels: Record<string, string>;
  lang: "en" | "hi" | "mr";
  inferred: Record<string, string>;
  inferred_questions?: Question[];
  offences: { id: string; label: string; evidence: string[] }[];
  understood: boolean;
  regime: Regime;
  procedure_code: string | null;
  primary_code: "IPC" | "BNS" | "both";
  sections: Section[];
  extra_laws: { law: string; sections: string; note: string }[];
  classifier: { available: boolean };
  similar_cases: {
    available: boolean;
    reason?: string;
    results: { id: string; snippet: string; matched_terms?: string[]; outcome_text?: string | null; ipc: string[]; shared_sections: string[]; similarity: number; source: string;
      plain?: { summary: string; outcome: string; relevance: string } }[];
    plain_by?: string;
  };
  next_steps: { steps: { title: string; detail: string }[]; helplines: { name: string; contact: string }[] };
  explanation: string | null;
  summary: string;
  disclaimer: string;
};

export type DocResult = {
  document: { kind: string; chars: number; pages?: number; pages_read?: number; ocr_pages?: number; note?: string };
  text: string;
  narrative: string;
  inferred: Record<string, string>;
  advice: { level: "ok" | "warning" | "info"; law: string | null; offence_date: string | null; message: string; procedure: string; ocr_check?: string };
  citations: {
    available: boolean;
    error?: string;
    converted_text: string | null;
    needs_attention?: number;
    citations: { found: string; code: string; target_code?: string; suggestion: string | null; ambiguous: boolean;
      items: { section: string; status: string; targets: string[]; notes: string[] }[] }[];
  };
};

export type LookupRow = { old: string | null; old_heading: string | null; new: string | null; new_heading: string | null;
  change: string | null; change_explained: string; mapping_explained: string; notes: string; row_id: string };
export type LookupResult = { code: string; section: string; found: boolean; status?: string; message: string;
  direction?: string; target_code?: string; results: LookupRow[] };
export type LawCheck = { date: string; law: string | null; decision: string; reason: string | null };
