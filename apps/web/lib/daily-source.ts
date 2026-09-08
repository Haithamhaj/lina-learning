export type StudentSourceAsset = {
  id: string;
  kind: "IMAGE" | "PDF" | "DOCUMENT";
  filename: string;
  content_type: string;
  size_bytes: number;
  preview_url: string;
};

const MAX_SOURCE_BYTES = 20 * 1024 * 1024;
const MAX_DOCX_BYTES = 10 * 1024 * 1024;
const TYPES: Record<string, string> = {
  jpg: "image/jpeg",
  jpeg: "image/jpeg",
  png: "image/png",
  webp: "image/webp",
  pdf: "application/pdf",
  docx: "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
};

export function validateDailySourceFile(file: File): string | null {
  const extension = file.name.split(".").pop()?.toLowerCase() ?? "";
  if (!TYPES[extension] || TYPES[extension] !== file.type) {
    return "Choose a PNG, JPEG, WEBP, PDF, or DOCX file.";
  }
  const maximum = extension === "docx" ? MAX_DOCX_BYTES : MAX_SOURCE_BYTES;
  if (file.size > maximum) {
    return extension === "docx" ? "DOCX files can be up to 10 MiB." : "Files can be up to 20 MiB.";
  }
  return null;
}

export function buildDailySourceSubmission({
  content,
  file,
  activeSourceId,
}: {
  content: string;
  file: File | null;
  activeSourceId: string | null;
}): { form: FormData; studentContent: string } {
  if (!file && !activeSourceId) throw new Error("A Student source is required.");
  const form = new FormData();
  form.set("content", content.trim());
  if (file) form.set("source", file);
  else if (activeSourceId) form.set("source_asset_id", activeSourceId);
  return { form, studentContent: content.trim() || "Help me with this." };
}

export function latestActiveStudentSource(
  messages: ReadonlyArray<{ role: string; source_asset?: StudentSourceAsset | null }>,
): StudentSourceAsset | null {
  for (let index = messages.length - 1; index >= 0; index -= 1) {
    const message = messages[index];
    if (message?.role === "student") return message.source_asset ?? null;
  }
  return null;
}
