export type Severity = "good" | "warning" | "critical";

export interface SectionFeedback {
  section: string;
  severity: Severity;
  score: number;
  feedback: string;
  suggestions: string[];
}

export interface BulletRewrite {
  original: string;
  improved: string;
  rationale: string;
}

export interface KeywordMatch {
  matched: string[];
  missing: string[];
  match_ratio: number;
}

export interface ReviewResult {
  overall_score: number;
  summary: string;
  strengths: string[];
  sections: SectionFeedback[];
  bullet_rewrites: BulletRewrite[];
  keywords: KeywordMatch;
  ats_notes: string[];
}

export type ReviewStatus = "pending" | "processing" | "completed" | "failed";

export interface ReviewStatusResponse {
  id: string;
  status: ReviewStatus;
  provider: string;
  created_at: string;
  completed_at: string | null;
  error: string | null;
  result: ReviewResult | null;
}

export interface ReviewListItem {
  id: string;
  status: string;
  provider: string;
  overall_score: number | null;
  created_at: string;
  job_description_preview: string | null;
}
