"use client";

import { useAuth } from "@clerk/nextjs";
import { ChangeEvent, FormEvent, useState } from "react";

import { Button } from "@/components/ui/button";
import { publicConfig } from "@/lib/public-config";

type UploadState =
  | { kind: "idle" }
  | { kind: "working" }
  | { kind: "success"; detail: string }
  | { kind: "error"; detail: string };

function fileToBase64(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onerror = () => reject(new Error("The selected file could not be read."));
    reader.onload = () => {
      const result = reader.result;
      if (typeof result !== "string") {
        reject(new Error("The selected file could not be read."));
        return;
      }
      resolve(result.split(",", 2)[1] ?? "");
    };
    reader.readAsDataURL(file);
  });
}

/** A deliberately small Parent/Admin intake form; processing is a later task. */
export function ContentUpload() {
  const { getToken } = useAuth();
  const [studentId, setStudentId] = useState("");
  const [gradeLevel, setGradeLevel] = useState("5");
  const [subject, setSubject] = useState("MATH");
  const [file, setFile] = useState<File | null>(null);
  const [uploadState, setUploadState] = useState<UploadState>({ kind: "idle" });

  const onFileChange = (event: ChangeEvent<HTMLInputElement>) => {
    setFile(event.target.files?.[0] ?? null);
    setUploadState({ kind: "idle" });
  };

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!file) {
      setUploadState({ kind: "error", detail: "Choose a PDF or Markdown file first." });
      return;
    }

    setUploadState({ kind: "working" });
    try {
      const token = await getToken();
      const response = await fetch(`${publicConfig.apiBaseUrl}/v1/content/documents`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({
          student_id: studentId,
          grade_level: Number(gradeLevel),
          subject,
          filename: file.name,
          content_type: file.type === "application/pdf" ? "application/pdf" : "text/markdown",
          content_base64: await fileToBase64(file),
        }),
      });
      const payload = (await response.json()) as { document_id?: string; status?: string; detail?: string };
      if (!response.ok || !payload.document_id || !payload.status) {
        throw new Error(payload.detail ?? "The book could not be uploaded.");
      }
      setUploadState({
        kind: "success",
        detail: `Original preserved. Processing status: ${payload.status}.`,
      });
    } catch (error) {
      setUploadState({
        kind: "error",
        detail: error instanceof Error ? error.message : "The book could not be uploaded.",
      });
    }
  };

  return (
    <form className="grid gap-4" onSubmit={submit}>
      <label className="grid gap-1 text-sm font-medium text-slate-700">
        Student profile ID
        <input
          className="rounded-xl border border-slate-200 bg-white px-3 py-2 text-ink"
          onChange={(event) => setStudentId(event.target.value)}
          placeholder="Student UUID"
          required
          value={studentId}
        />
      </label>
      <div className="grid gap-4 sm:grid-cols-2">
        <label className="grid gap-1 text-sm font-medium text-slate-700">
          Grade
          <select className="rounded-xl border border-slate-200 bg-white px-3 py-2 text-ink" value={gradeLevel} onChange={(event) => setGradeLevel(event.target.value)}>
            <option value="5">Grade 5</option>
          </select>
        </label>
        <label className="grid gap-1 text-sm font-medium text-slate-700">
          Subject
          <select className="rounded-xl border border-slate-200 bg-white px-3 py-2 text-ink" value={subject} onChange={(event) => setSubject(event.target.value)}>
            <option value="MATH">Math</option>
          </select>
        </label>
      </div>
      <label className="grid gap-1 text-sm font-medium text-slate-700">
        Grade book
        <input accept="application/pdf,.pdf,.md,.markdown" className="rounded-xl border border-dashed border-slate-300 bg-white px-3 py-2 text-sm" onChange={onFileChange} required type="file" />
      </label>
      <p className="text-xs leading-5 text-slate-500">
        PDF books and Markdown test fixtures are accepted. The original file is kept unchanged; an identical upload is safely reused instead of stored twice.
      </p>
      <div className="flex items-center gap-3">
        <Button disabled={uploadState.kind === "working"} type="submit">
          {uploadState.kind === "working" ? "Preserving book…" : "Upload Grade book"}
        </Button>
        {uploadState.kind === "success" ? <p className="text-sm text-emerald-700" role="status">{uploadState.detail}</p> : null}
        {uploadState.kind === "error" ? <p className="text-sm text-red-700" role="alert">{uploadState.detail}</p> : null}
      </div>
    </form>
  );
}
