// Thin client for the FastAPI backend. Calls go to /api/* and are proxied to
// the backend by the rewrite in next.config.mjs.

export interface JobDescription {
  id: number;
  title: string;
  text: string;
  created_at: string;
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
