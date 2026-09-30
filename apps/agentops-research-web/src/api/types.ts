export interface DigestSummary {
  run_id: string;
  research_interest: string | null;
  date_from: string | null;
  date_to: string | null;
  generated_at: string | null;
  top_paper_title: string | null;
  model: string | null;
  data_source?: string | null;
}

export interface Candidate {
  paper_id: string;
  title: string;
  score: number;
  rationale: string;
}

export interface PaperSection {
  paper_id: string;
  summary: string;
}

export interface DigestFigure {
  caption: string;
  description: string;
  filename: string | null;
}

export interface DigestDetail {
  run_id: string;
  research_interest: string | null;
  date_from: string | null;
  date_to: string | null;
  generated_at: string | null;
  digest: string;
  candidates: Candidate[];
  sections: PaperSection[];
  figures: Record<string, DigestFigure[]>;
  model: string | null;
  data_source?: string | null;
  status?: string;
  error?: string | null;
}

export interface CreateDigestRequest {
  research_interest: string;
  date_from: string;
  date_to: string;
  model?: string;
}

export interface CreateDigestResponse {
  run_id: string;
  status: "running" | "succeeded" | "failed";
  model: string;
}

export interface SavedSearch {
  research_interest: string;
  date_from: string;
  date_to: string;
  savedAt: string;
}
