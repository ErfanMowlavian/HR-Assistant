// Thin client for the FastAPI backend. Calls go to /api/* and are proxied to
// the backend by the rewrite in next.config.mjs.

export interface JDRequirements {
  required_skills: string[];
  nice_to_have_skills: string[];
  min_years_experience: number;
  education: string | null;
  seniority: string | null;
}

export interface JobDescription {
  id: number;
  title: string;
  text: string;
  created_at: string;
  requirements: JDRequirements | null;
  extraction_ok: boolean;
}

export interface JobDescriptionCreate {
  title: string;
  text: string;
}

async function handle<T>(res: Response): Promise<T> {
  if (!res.ok) {
    throw new Error(`خطای سرور (${res.status})`);
  }
  return (await res.json()) as T;
}

export async function listJobs(): Promise<JobDescription[]> {
  return handle(await fetch("/api/jobs", { cache: "no-store" }));
}

export async function createJob(
  payload: JobDescriptionCreate
): Promise<JobDescription> {
  const res = await fetch("/api/jobs", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  return handle(res);
}

export async function updateRequirements(
  jobId: number,
  requirements: JDRequirements
): Promise<JobDescription> {
  const res = await fetch(`/api/jobs/${jobId}/requirements`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(requirements),
  });
  return handle(res);
}

export interface ResumeFields {
  skills: string[];
  total_years_experience: number;
  titles: string[];
  education: string | null;
}

export interface Submission {
  id: number;
  job_id: number;
  applicant_name: string;
  resume_text: string;
  resume_fields: ResumeFields | null;
  created_at: string;
  extraction_ok: boolean;
}

export async function createSubmission(
  jobId: number,
  payload: { applicant_name: string; resume_text: string }
): Promise<Submission> {
  const res = await fetch(`/api/jobs/${jobId}/submissions`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  return handle(res);
}

// --- Scoring & ranking (Issue #5) ---

export type SkillVerdict = "yes" | "partial" | "no";

export interface ComponentScore {
  key: string;
  label: string;
  applicable: boolean;
  score: number | null;
  weight: number;
  contribution: number;
}

export interface SkillJudgment {
  skill: string;
  verdict: SkillVerdict;
  reason: string | null;
  kind: "required" | "nice";
}

export interface ScoreWeights {
  required_skills: number;
  nice_to_have_skills: number;
  experience: number;
  education: number;
}

export interface Evaluation {
  match_score: number;
  components: ComponentScore[];
  judgments: SkillJudgment[];
  weights: ScoreWeights;
}

export interface RankedCandidate {
  submission_id: number;
  applicant_name: string;
  created_at: string;
  evaluation: Evaluation | null;
}

export async function getRanking(jobId: number): Promise<RankedCandidate[]> {
  return handle(await fetch(`/api/jobs/${jobId}/ranking`, { cache: "no-store" }));
}

// "Rank now" (Issue #7): re-run the scoring pipeline live and return the fresh
// ranking — the on-demand proof, separate from the stored-data read above.
export async function rankNow(jobId: number): Promise<RankedCandidate[]> {
  return handle(await fetch(`/api/jobs/${jobId}/rank`, { method: "POST" }));
}
