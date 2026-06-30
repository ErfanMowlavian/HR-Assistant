"use client";

import * as React from "react";

import { CreateJobForm } from "@/components/create-job-form";
import { JobList } from "@/components/job-list";
import { listJobs, type JobDescription } from "@/lib/api";

export default function HomePage() {
  const [jobs, setJobs] = React.useState<JobDescription[]>([]);
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState<string | null>(null);

  const refresh = React.useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setJobs(await listJobs());
    } catch (err) {
      setError(err instanceof Error ? err.message : "خطای ناشناخته");
    } finally {
      setLoading(false);
    }
  }, []);

  React.useEffect(() => {
    void refresh();
  }, [refresh]);

  const handleJobUpdated = React.useCallback((updated: JobDescription) => {
    setJobs((prev) => prev.map((j) => (j.id === updated.id ? updated : j)));
  }, []);

  return (
    <main className="container max-w-3xl py-10">
      <header className="mb-8 space-y-1">
        <h1 className="text-2xl font-bold">داشبورد منابع انسانی</h1>
        <p className="text-muted-foreground">
          شرح شغل‌ها را بسازید و مدیریت کنید.
        </p>
      </header>

      <div className="space-y-8">
        <CreateJobForm onCreated={refresh} />

        <section className="space-y-4">
          <h2 className="text-lg font-semibold">شرح شغل‌های ثبت‌شده</h2>
          {error && <p className="text-sm text-destructive">{error}</p>}
          {loading ? (
            <p className="text-sm text-muted-foreground">در حال بارگذاری…</p>
          ) : (
            <JobList jobs={jobs} onJobUpdated={handleJobUpdated} />
          )}
        </section>
      </div>
    </main>
  );
}
