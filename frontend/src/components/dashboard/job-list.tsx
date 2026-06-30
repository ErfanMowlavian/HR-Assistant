"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { RequirementsEditor } from "@/components/dashboard/requirements-editor";
import { RankingPanel } from "@/components/dashboard/ranking-panel";
import type { JobDescription } from "@/lib/api";

function formatDate(iso: string): string {
  try {
    return new Intl.DateTimeFormat("fa-IR", {
      dateStyle: "medium",
      timeStyle: "short",
    }).format(new Date(iso));
  } catch {
    return iso;
  }
}

export function JobList({
  jobs,
  onJobUpdated,
}: {
  jobs: JobDescription[];
  onJobUpdated: (updated: JobDescription) => void;
}) {
  if (jobs.length === 0) {
    return (
      <Card>
        <CardContent className="py-10 text-center text-muted-foreground">
          هنوز شرح شغلی ثبت نشده است. اولین مورد را از فرم بالا بسازید.
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-3">
      {jobs.map((job) => (
        <Card key={job.id}>
          <CardHeader className="pb-2">
            <CardTitle className="flex items-center justify-between gap-4">
              <span>{job.title}</span>
              <span className="text-xs font-normal text-muted-foreground">
                {formatDate(job.created_at)}
              </span>
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <p className="line-clamp-3 whitespace-pre-line text-sm text-muted-foreground">
              {job.text}
            </p>
            <RequirementsEditor job={job} onUpdated={onJobUpdated} />
            <RankingPanel jobId={job.id} />
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
