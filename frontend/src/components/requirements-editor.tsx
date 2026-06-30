"use client";

import * as React from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  updateRequirements,
  type JDRequirements,
  type JobDescription,
} from "@/lib/api";

function toList(value: string): string[] {
  return value
    .split(/[،,]/)
    .map((s) => s.trim())
    .filter(Boolean);
}

function SkillChips({ items }: { items: string[] }) {
  if (items.length === 0) {
    return <span className="text-sm text-muted-foreground">—</span>;
  }
  return (
    <div className="flex flex-wrap gap-1.5">
      {items.map((s) => (
        <Badge key={s} variant="secondary">
          {s}
        </Badge>
      ))}
    </div>
  );
}

export function RequirementsEditor({
  job,
  onUpdated,
}: {
  job: JobDescription;
  onUpdated: (updated: JobDescription) => void;
}) {
  const [editing, setEditing] = React.useState(false);
  const [saving, setSaving] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);

  const req: JDRequirements = job.requirements ?? {
    required_skills: [],
    nice_to_have_skills: [],
    min_years_experience: 0,
    education: null,
    seniority: null,
  };

  const [requiredSkills, setRequiredSkills] = React.useState(
    req.required_skills.join("، ")
  );
  const [niceSkills, setNiceSkills] = React.useState(
    req.nice_to_have_skills.join("، ")
  );
  const [minYears, setMinYears] = React.useState(String(req.min_years_experience));
  const [education, setEducation] = React.useState(req.education ?? "");
  const [seniority, setSeniority] = React.useState(req.seniority ?? "");

  async function handleSave() {
    setSaving(true);
    setError(null);
    try {
      const updated = await updateRequirements(job.id, {
        required_skills: toList(requiredSkills),
        nice_to_have_skills: toList(niceSkills),
        min_years_experience: Number.parseInt(minYears, 10) || 0,
        education: education.trim() || null,
        seniority: seniority.trim() || null,
      });
      onUpdated(updated);
      setEditing(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : "خطای ناشناخته");
    } finally {
      setSaving(false);
    }
  }

  if (!job.extraction_ok && !editing) {
    return (
      <div className="space-y-2 rounded-md bg-muted/50 p-3 text-sm">
        <p className="text-muted-foreground">
          استخراج خودکار نیازمندی‌ها انجام نشد. می‌توانید آن‌ها را دستی وارد کنید.
        </p>
        <Button size="sm" variant="outline" onClick={() => setEditing(true)}>
          وارد کردن نیازمندی‌ها
        </Button>
      </div>
    );
  }

  if (!editing) {
    return (
      <div className="space-y-3 rounded-md bg-muted/50 p-3">
        <Field label="مهارت‌های الزامی">
          <SkillChips items={req.required_skills} />
        </Field>
        <Field label="مهارت‌های امتیازی">
          <SkillChips items={req.nice_to_have_skills} />
        </Field>
        <div className="grid grid-cols-3 gap-3 text-sm">
          <Field label="حداقل سابقه">
            <span>{req.min_years_experience} سال</span>
          </Field>
          <Field label="تحصیلات">
            <span>{req.education || "—"}</span>
          </Field>
          <Field label="سطح ارشدیت">
            <span>{req.seniority || "—"}</span>
          </Field>
        </div>
        <Button size="sm" variant="outline" onClick={() => setEditing(true)}>
          ویرایش نیازمندی‌ها
        </Button>
      </div>
    );
  }

  return (
    <div className="space-y-3 rounded-md border p-3">
      <div className="space-y-2">
        <Label htmlFor={`req-${job.id}`}>مهارت‌های الزامی (با ویرگول جدا کنید)</Label>
        <Input
          id={`req-${job.id}`}
          value={requiredSkills}
          onChange={(e) => setRequiredSkills(e.target.value)}
        />
      </div>
      <div className="space-y-2">
        <Label htmlFor={`nice-${job.id}`}>مهارت‌های امتیازی</Label>
        <Input
          id={`nice-${job.id}`}
          value={niceSkills}
          onChange={(e) => setNiceSkills(e.target.value)}
        />
      </div>
      <div className="grid grid-cols-3 gap-3">
        <div className="space-y-2">
          <Label htmlFor={`years-${job.id}`}>حداقل سابقه (سال)</Label>
          <Input
            id={`years-${job.id}`}
            type="number"
            min={0}
            value={minYears}
            onChange={(e) => setMinYears(e.target.value)}
          />
        </div>
        <div className="space-y-2">
          <Label htmlFor={`edu-${job.id}`}>تحصیلات</Label>
          <Input
            id={`edu-${job.id}`}
            value={education}
            onChange={(e) => setEducation(e.target.value)}
          />
        </div>
        <div className="space-y-2">
          <Label htmlFor={`sen-${job.id}`}>سطح ارشدیت</Label>
          <Input
            id={`sen-${job.id}`}
            value={seniority}
            onChange={(e) => setSeniority(e.target.value)}
          />
        </div>
      </div>
      {error && <p className="text-sm text-destructive">{error}</p>}
      <div className="flex gap-2">
        <Button size="sm" onClick={handleSave} disabled={saving}>
          {saving ? "در حال ذخیره…" : "ذخیرهٔ تغییرات"}
        </Button>
        <Button
          size="sm"
          variant="ghost"
          onClick={() => setEditing(false)}
          disabled={saving}
        >
          انصراف
        </Button>
      </div>
    </div>
  );
}

function Field({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) {
  return (
    <div className="space-y-1">
      <p className="text-xs font-medium text-muted-foreground">{label}</p>
      {children}
    </div>
  );
}
