"use client";

import * as React from "react";

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
import { createJob } from "@/lib/api";

export function CreateJobForm({ onCreated }: { onCreated: () => void }) {
  const [title, setTitle] = React.useState("");
  const [text, setText] = React.useState("");
  const [submitting, setSubmitting] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await createJob({ title: title.trim(), text: text.trim() });
      setTitle("");
      setText("");
      onCreated();
    } catch (err) {
      setError(err instanceof Error ? err.message : "خطای ناشناخته");
    } finally {
      setSubmitting(false);
    }
  }

  const canSubmit = title.trim().length > 0 && text.trim().length > 0 && !submitting;

  return (
    <Card>
      <CardHeader>
        <CardTitle>ایجاد شرح شغل تازه</CardTitle>
        <CardDescription>
          عنوان نقش و متن کامل آگهی را به فارسی وارد کنید.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="title">عنوان شغل</Label>
            <Input
              id="title"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="مثلاً: مهندس نرم‌افزار ارشد"
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="text">متن شرح شغل</Label>
            <Textarea
              id="text"
              value={text}
              onChange={(e) => setText(e.target.value)}
              placeholder="مسئولیت‌ها، مهارت‌های موردنیاز، سابقهٔ کار و …"
            />
          </div>
          {error && <p className="text-sm text-destructive">{error}</p>}
          <Button type="submit" disabled={!canSubmit}>
            {submitting ? "در حال ذخیره…" : "ذخیرهٔ شرح شغل"}
          </Button>
        </form>
      </CardContent>
    </Card>
  );
}
