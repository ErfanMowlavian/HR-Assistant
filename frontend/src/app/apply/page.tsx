"use client";

import * as React from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
  createSubmission,
  listJobs,
  uploadResume,
  type JobDescription,
  type Submission,
} from "@/lib/api";
import { cn } from "@/lib/utils";

export default function ApplyPage() {
  const [jobs, setJobs] = React.useState<JobDescription[]>([]);
  const [loading, setLoading] = React.useState(true);
  const [selectedId, setSelectedId] = React.useState<number | null>(null);
  const [name, setName] = React.useState("");
  const [resume, setResume] = React.useState("");
  const [submitting, setSubmitting] = React.useState(false);
  const [uploading, setUploading] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);
  const [result, setResult] = React.useState<Submission | null>(null);
  const fileInputRef = React.useRef<HTMLInputElement>(null);

  React.useEffect(() => {
    listJobs()
      .then(setJobs)
      .catch((e) => setError(e instanceof Error ? e.message : "خطا"))
      .finally(() => setLoading(false));
  }, []);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (selectedId === null) return;
    setSubmitting(true);
    setError(null);
    setResult(null);
    try {
      const submission = await createSubmission(selectedId, {
        applicant_name: name.trim(),
        resume_text: resume.trim(),
      });
      setResult(submission);
      setResume("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "خطای ناشناخته");
    } finally {
      setSubmitting(false);
    }
  }

  async function handleUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    e.target.value = ""; // allow re-selecting the same file after an error
    if (!file || selectedId === null) return;
    setUploading(true);
    setError(null);
    setResult(null);
    try {
      const submission = await uploadResume(selectedId, name.trim(), file);
      setResult(submission);
      setResume("");
    } catch (err) {
      // The backend nudges to paste when a PDF extracts to garbled text.
      setError(err instanceof Error ? err.message : "خطای ناشناخته");
    } finally {
      setUploading(false);
    }
  }

  const busy = submitting || uploading;
  const canSubmit =
    selectedId !== null &&
    name.trim().length > 0 &&
    resume.trim().length > 0 &&
    !busy;
  const canUpload = selectedId !== null && name.trim().length > 0 && !busy;

  return (
    <main className="container max-w-3xl py-10">
      <header className="mb-8 space-y-1">
        <h1 className="text-2xl font-bold">ارسال رزومه</h1>
        <p className="text-muted-foreground">
          یک آگهی شغلی را انتخاب کنید و رزومه‌تان را برای آن ثبت کنید.
        </p>
      </header>

      <div className="space-y-8">
        <section className="space-y-3">
          <h2 className="text-lg font-semibold">۱. انتخاب آگهی شغلی</h2>
          {loading ? (
            <p className="text-sm text-muted-foreground">در حال بارگذاری…</p>
          ) : jobs.length === 0 ? (
            <Card>
              <CardContent className="py-8 text-center text-muted-foreground">
                در حال حاضر آگهی فعالی وجود ندارد.
              </CardContent>
            </Card>
          ) : (
            <div className="grid gap-3">
              {jobs.map((job) => (
                <button
                  key={job.id}
                  type="button"
                  onClick={() => setSelectedId(job.id)}
                  className={cn(
                    "rounded-lg border p-4 text-right transition-colors hover:bg-accent",
                    selectedId === job.id && "border-primary ring-2 ring-ring"
                  )}
                >
                  <div className="font-medium">{job.title}</div>
                  <p className="mt-1 line-clamp-2 text-sm text-muted-foreground">
                    {job.text}
                  </p>
                  {job.requirements && job.requirements.required_skills.length > 0 && (
                    <div className="mt-2 flex flex-wrap gap-1.5">
                      {job.requirements.required_skills.map((s) => (
                        <Badge key={s} variant="secondary">
                          {s}
                        </Badge>
                      ))}
                    </div>
                  )}
                </button>
              ))}
            </div>
          )}
        </section>

        <section className="space-y-3">
          <h2 className="text-lg font-semibold">۲. ثبت رزومه</h2>
          <Card>
            <CardHeader>
              <CardTitle>رزومهٔ شما</CardTitle>
              <CardDescription>
                نام و متن رزومه را وارد کنید. می‌توانید فارسی و انگلیسی را با هم
                بنویسید.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <form onSubmit={handleSubmit} className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="name">نام نمایشی</Label>
                  <Input
                    id="name"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    placeholder="مثلاً: سارا رضایی"
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="resume">متن رزومه</Label>
                  <Textarea
                    id="resume"
                    value={resume}
                    onChange={(e) => setResume(e.target.value)}
                    placeholder="سوابق شغلی، مهارت‌ها، تحصیلات و …"
                    className="min-h-[180px]"
                  />
                </div>
                {error && <p className="text-sm text-destructive">{error}</p>}
                <div className="flex flex-wrap items-center gap-3">
                  <Button type="submit" disabled={!canSubmit}>
                    {submitting
                      ? "در حال ارسال…"
                      : selectedId === null
                        ? "ابتدا یک آگهی انتخاب کنید"
                        : "ارسال رزومه"}
                  </Button>
                  <span className="text-sm text-muted-foreground">یا</span>
                  <input
                    ref={fileInputRef}
                    type="file"
                    accept="application/pdf,.pdf"
                    className="hidden"
                    onChange={handleUpload}
                  />
                  <Button
                    type="button"
                    variant="outline"
                    disabled={!canUpload}
                    onClick={() => fileInputRef.current?.click()}
                  >
                    {uploading ? "در حال پردازش PDF…" : "آپلود PDF"}
                  </Button>
                </div>
                <p className="text-xs text-muted-foreground">
                  وارد کردن متن، مسیر اصلی و مطمئن است. آپلود PDF بهترین تلاش است؛
                  اگر متن فارسی درست استخراج نشود، از شما خواسته می‌شود متن را وارد
                  کنید.
                </p>
              </form>

              {result && (
                <div className="mt-4 rounded-md bg-muted/50 p-3 text-sm">
                  <p className="font-medium text-foreground">
                    رزومهٔ شما با موفقیت ثبت شد. ✔
                  </p>
                  {result.extraction_ok && result.resume_fields ? (
                    <p className="mt-1 text-muted-foreground">
                      مهارت‌های شناسایی‌شده:{" "}
                      {result.resume_fields.skills.join("، ") || "—"}
                    </p>
                  ) : (
                    <p className="mt-1 text-muted-foreground">
                      رزومه ذخیره شد؛ استخراج خودکار مهارت‌ها بعداً انجام خواهد شد.
                    </p>
                  )}
                </div>
              )}
            </CardContent>
          </Card>
        </section>
      </div>
    </main>
  );
}
