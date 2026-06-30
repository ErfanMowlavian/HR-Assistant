"use client";

import * as React from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  getRanking,
  rankNow,
  type Evaluation,
  type RankedCandidate,
  type SkillVerdict,
} from "@/lib/api";
import { cn } from "@/lib/utils";

const VERDICT_LABEL: Record<SkillVerdict, string> = {
  yes: "بله",
  partial: "تاحدی",
  no: "خیر",
};

const VERDICT_CLASS: Record<SkillVerdict, string> = {
  yes: "border-green-600/40 bg-green-600/10 text-green-700 dark:text-green-400",
  partial: "border-amber-500/40 bg-amber-500/10 text-amber-700 dark:text-amber-400",
  no: "border-red-600/40 bg-red-600/10 text-red-700 dark:text-red-400",
};

function pct(n: number): string {
  return `${Math.round(n * 100)}٪`;
}

function ScoreBreakdown({ evaluation }: { evaluation: Evaluation }) {
  return (
    <div className="space-y-2">
      {evaluation.components
        .filter((c) => c.applicable)
        .map((c) => (
          <div key={c.key} className="space-y-1">
            <div className="flex items-center justify-between text-xs text-muted-foreground">
              <span>{c.label}</span>
              <span>{c.score === null ? "—" : pct(c.score)}</span>
            </div>
            <div className="h-1.5 overflow-hidden rounded-full bg-muted">
              <div
                className="h-full rounded-full bg-primary"
                style={{ width: `${Math.round((c.score ?? 0) * 100)}%` }}
              />
            </div>
          </div>
        ))}
    </div>
  );
}

function SkillJudgments({ evaluation }: { evaluation: Evaluation }) {
  if (evaluation.judgments.length === 0) return null;
  return (
    <div className="flex flex-wrap gap-1.5">
      {evaluation.judgments.map((j) => (
        <span
          key={`${j.kind}:${j.skill}`}
          className={cn(
            "inline-flex items-center gap-1 rounded-md border px-2 py-0.5 text-xs",
            VERDICT_CLASS[j.verdict]
          )}
          title={j.reason ?? undefined}
        >
          <span className="font-medium">{j.skill}</span>
          <span className="opacity-70">{VERDICT_LABEL[j.verdict]}</span>
          {j.kind === "nice" && <span className="opacity-50">(امتیازی)</span>}
        </span>
      ))}
    </div>
  );
}

function CandidateRow({ candidate, rank }: { candidate: RankedCandidate; rank: number }) {
  const ev = candidate.evaluation;
  return (
    <div className="rounded-lg border p-3">
      <div className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-muted text-xs font-bold">
            {rank}
          </span>
          <span className="font-medium">{candidate.applicant_name}</span>
        </div>
        {candidate.status === "processing" ? (
          <Badge variant="secondary" className="gap-1.5">
            <span className="inline-block h-3 w-3 animate-spin rounded-full border-2 border-current border-t-transparent" />
            در حال محاسبه…
          </Badge>
        ) : ev ? (
          <span className="text-sm font-bold tabular-nums">{pct(ev.match_score)}</span>
        ) : (
          <Badge variant="secondary">ارزیابی‌نشده</Badge>
        )}
      </div>
      {ev && (
        <div className="mt-3 space-y-3">
          <ScoreBreakdown evaluation={ev} />
          <SkillJudgments evaluation={ev} />
        </div>
      )}
    </div>
  );
}

export function RankingPanel({ jobId }: { jobId: number }) {
  const [open, setOpen] = React.useState(false);
  const [candidates, setCandidates] = React.useState<RankedCandidate[] | null>(null);
  const [loading, setLoading] = React.useState(false);
  const [ranking, setRanking] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);

  const load = React.useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setCandidates(await getRanking(jobId));
    } catch (e) {
      setError(e instanceof Error ? e.message : "خطا");
    } finally {
      setLoading(false);
    }
  }, [jobId]);

  // "Rank now": re-run the pipeline live (the read path above renders stored
  // results without a model call; this proves scoring on demand).
  const rankLive = React.useCallback(async () => {
    setRanking(true);
    setError(null);
    try {
      setCandidates(await rankNow(jobId));
    } catch (e) {
      setError(e instanceof Error ? e.message : "خطا");
    } finally {
      setRanking(false);
    }
  }, [jobId]);

  function toggle() {
    const next = !open;
    setOpen(next);
    if (next && candidates === null) void load();
  }

  // Re-scoring (a fresh submission, edited requirements, or "rank now") runs in
  // the background, so candidates come back "processing". Quietly re-poll until
  // every row settles, then stop — no spinner toggling on the buttons.
  React.useEffect(() => {
    if (!open) return;
    if (!candidates?.some((c) => c.status === "processing")) return;
    const timer = setTimeout(async () => {
      try {
        setCandidates(await getRanking(jobId));
      } catch {
        /* transient; the next effect run retries */
      }
    }, 2500);
    return () => clearTimeout(timer);
  }, [open, candidates, jobId]);

  const busy = loading || ranking;

  return (
    <div className="border-t pt-3">
      <div className="flex items-center justify-between">
        <Button variant="ghost" size="sm" onClick={toggle} className="px-2">
          {open ? "▼" : "◀"} داوطلبان رتبه‌بندی‌شده
        </Button>
        {open && (
          <div className="flex items-center gap-2">
            <Button variant="default" size="sm" onClick={rankLive} disabled={busy}>
              {ranking ? "در حال رتبه‌بندی…" : "رتبه‌بندی زنده"}
            </Button>
            <Button variant="outline" size="sm" onClick={load} disabled={busy}>
              {loading ? "در حال بارگذاری…" : "به‌روزرسانی"}
            </Button>
          </div>
        )}
      </div>

      {open && (
        <div className="mt-3 space-y-2">
          {error && <p className="text-sm text-destructive">{error}</p>}
          {loading && candidates === null ? (
            <p className="text-sm text-muted-foreground">در حال بارگذاری…</p>
          ) : candidates && candidates.length === 0 ? (
            <p className="text-sm text-muted-foreground">
              هنوز داوطلبی برای این آگهی رزومه نفرستاده است.
            </p>
          ) : (
            candidates?.map((c, i) => (
              <CandidateRow key={c.submission_id} candidate={c} rank={i + 1} />
            ))
          )}
        </div>
      )}
    </div>
  );
}
