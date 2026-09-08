"use client";

import { type ChangeEvent, useEffect, useRef, useState } from "react";

import { Button } from "@/components/ui/button";
import type { StudentSourceAsset } from "@/lib/daily-source";
import { validateDailySourceFile } from "@/lib/daily-source";

type TokenGetter = () => Promise<string | null>;

export function sourceMetadataFromFile(file: File, id = "pending-source"): StudentSourceAsset {
  const extension = file.name.split(".").pop()?.toLowerCase();
  return {
    id,
    kind: file.type.startsWith("image/") ? "IMAGE" : extension === "pdf" ? "PDF" : "DOCUMENT",
    filename: file.name,
    content_type: file.type,
    size_bytes: file.size,
    preview_url: "",
  };
}

export function DailySourceInput({
  file,
  activeSource,
  disabled,
  onFile,
  onDismissActive,
  onError,
}: {
  file: File | null;
  activeSource: StudentSourceAsset | null;
  disabled: boolean;
  onFile: (file: File | null) => void;
  onDismissActive: () => void;
  onError: (message: string) => void;
}) {
  const inputRef = useRef<HTMLInputElement | null>(null);
  const [localPreview, setLocalPreview] = useState<string | null>(null);
  const shown = file ? sourceMetadataFromFile(file) : activeSource;
  useEffect(() => {
    if (!file || !file.type.startsWith("image/")) {
      setLocalPreview(null);
      return;
    }
    const url = URL.createObjectURL(file);
    setLocalPreview(url);
    return () => URL.revokeObjectURL(url);
  }, [file]);
  const select = (event: ChangeEvent<HTMLInputElement>) => {
    const next = event.target.files?.[0] ?? null;
    event.target.value = "";
    if (!next) return;
    const validationError = validateDailySourceFile(next);
    if (validationError) {
      onError(validationError);
      return;
    }
    onError("");
    onFile(next);
  };
  return (
    <div className="order-1 sm:col-span-3">
      <input ref={inputRef} type="file" className="sr-only" accept=".jpg,.jpeg,.png,.webp,.pdf,.docx" onChange={select} />
      <div className="flex flex-wrap items-center gap-2">
        <Button type="button" variant="secondary" className="min-h-10 rounded-full px-3" disabled={disabled} onClick={() => inputRef.current?.click()}>
          <span aria-hidden="true">＋</span> Add photo or file
        </Button>
        {shown ? <div className="flex min-w-0 items-center gap-2 rounded-2xl border border-[#d9d3ff] bg-[#f6f3ff] px-3 py-2 text-xs text-[#463b85]">
          <span aria-hidden="true">{shown.kind === "IMAGE" ? "🖼" : shown.kind === "PDF" ? "PDF" : "DOC"}</span>
          <span className="max-w-52 truncate">{shown.filename}</span>
          <span className="text-[#7166a7]">{file ? "ready to send" : "in this conversation"}</span>
          <button type="button" className="rounded-full px-1 font-bold hover:bg-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#7d70df]" aria-label={file ? `Remove ${shown.filename}` : `Stop using ${shown.filename}`} onClick={() => file ? onFile(null) : onDismissActive()}>×</button>
        </div> : null}
      </div>
      {localPreview ? <img src={localPreview} alt={`Ready to send: ${file?.name ?? "Student source"}`} className="mt-2 max-h-40 max-w-64 rounded-xl border border-[#d9d3ff] object-contain" /> : null}
    </div>
  );
}

export function StudentSourceCard({
  source,
  apiBaseUrl,
  getToken,
}: {
  source: StudentSourceAsset;
  apiBaseUrl: string;
  getToken: TokenGetter;
}) {
  const [objectUrl, setObjectUrl] = useState<string | null>(null);
  const [failed, setFailed] = useState(false);
  useEffect(() => {
    let cancelled = false;
    let localUrl: string | null = null;
    void getToken().then(async (token) => {
      const response = await fetch(`${apiBaseUrl.replace(/\/$/, "")}/v1/student${source.preview_url}`, {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      });
      if (!response.ok) throw new Error("Source preview unavailable.");
      return response.blob();
    }).then((blob) => {
      if (cancelled) return;
      localUrl = URL.createObjectURL(blob);
      setObjectUrl(localUrl);
    }).catch(() => { if (!cancelled) setFailed(true); });
    return () => {
      cancelled = true;
      if (localUrl) URL.revokeObjectURL(localUrl);
    };
  }, [apiBaseUrl, getToken, source.preview_url]);

  if (source.kind === "IMAGE" && objectUrl) {
    return <img src={objectUrl} alt={`Student source: ${source.filename}`} className="mt-2 max-h-56 max-w-full rounded-xl border border-white/40 object-contain" />;
  }
  return <div className="mt-2 flex items-center gap-2 rounded-xl border border-white/40 bg-white/10 px-3 py-2 text-xs">
    <span aria-hidden="true">{source.kind === "PDF" ? "PDF" : source.kind === "DOCUMENT" ? "DOC" : "🖼"}</span>
    <span className="max-w-52 truncate">{source.filename}</span>
    {objectUrl ? <a href={objectUrl} target="_blank" rel="noreferrer" className="underline">Open</a> : <span>{failed ? "Preview unavailable" : "Loading…"}</span>}
  </div>;
}
