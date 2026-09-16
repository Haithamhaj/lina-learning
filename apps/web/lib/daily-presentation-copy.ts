export type DailyDirection = "ltr" | "rtl";

export type DailyPresentationCopy = {
  student: string;
  linaThinking: string;
  canvas: {
    workspaceLabel: string;
    currentSceneHeading: string;
    preparingHeading: string;
    updatingHeading: string;
    failureHeading: string;
    statusHeading: string;
    saving: string;
    preparing: (elapsedSeconds: number) => string;
    elapsed: (elapsedSeconds: number) => string;
    failed: string;
    statusUnavailable: string;
  };
  voice: {
    record: string;
    stop: string;
    cancel: string;
    requestingPermission: string;
    recording: (elapsed: string) => string;
    transcribing: string;
    unsupported: string;
    unavailable: string;
  };
  source: {
    add: string;
    ready: string;
    active: string;
    remove: (filename: string) => string;
    stopUsing: (filename: string) => string;
    readyPreview: (filename: string) => string;
    studentSource: (filename: string) => string;
    open: string;
    previewUnavailable: string;
    loading: string;
  };
};

export function dailyPresentationCopy(direction: DailyDirection): DailyPresentationCopy {
  if (direction === "rtl") {
    return {
      student: "أنتِ",
      linaThinking: "لينا تفكّر…",
      canvas: {
        workspaceLabel: "مساحة Canvas التعليمية",
        currentSceneHeading: "تفاعلي مع المشهد الحالي",
        preparingHeading: "جارٍ تجهيز شرح بصري",
        updatingHeading: "جارٍ تجهيز تحديث بصري",
        failureHeading: "لم يكتمل الرسم",
        statusHeading: "حالة الرسم",
        saving: "جارٍ الحفظ…",
        preparing: (elapsedSeconds) => elapsedSeconds < 10
          ? "أجهّز لك الرسم…"
          : elapsedSeconds < 30
            ? "أبني التمثيل البصري خطوة بخطوة…"
            : "الرسم ما زال قيد التجهيز. يمكنكِ متابعة الشرح معي إلى أن يظهر.",
        elapsed: (elapsedSeconds) => `جارٍ العمل منذ ${elapsedSeconds} ثانية`,
        failed: "لم يكتمل التمثيل البصري هذه المرة. يمكنكِ متابعة المحادثة أو طلب شرح مختلف.",
        statusUnavailable: "تعذر تحديث حالة الرسم الآن.",
      },
      voice: {
        record: "سجّلي رسالة صوتية",
        stop: "أوقفي التسجيل وحوّليه إلى نص",
        cancel: "إلغاء",
        requestingPermission: "جارٍ طلب إذن الميكروفون…",
        recording: (elapsed) => `جارٍ التسجيل ${elapsed}. أوقفيه عندما تكونين مستعدة.`,
        transcribing: "جارٍ تحويل التسجيل إلى نص…",
        unsupported: "التسجيل الصوتي غير مدعوم في هذا المتصفح. يمكنكِ متابعة الكتابة.",
        unavailable: "التسجيل الصوتي غير متاح الآن.",
      },
      source: {
        add: "أضيفي صورة أو ملفًا",
        ready: "جاهز للإرسال",
        active: "مستخدم في هذه المحادثة",
        remove: (filename) => `إزالة ${filename}`,
        stopUsing: (filename) => `التوقف عن استخدام ${filename}`,
        readyPreview: (filename) => `جاهز للإرسال: ${filename}`,
        studentSource: (filename) => `مادة الطالبة: ${filename}`,
        open: "فتح",
        previewUnavailable: "المعاينة غير متاحة",
        loading: "جارٍ التحميل…",
      },
    };
  }

  return {
    student: "You",
    linaThinking: "Lina is thinking…",
    canvas: {
      workspaceLabel: "Learning Canvas",
      currentSceneHeading: "Work with the current scene",
      preparingHeading: "Preparing a visual explanation",
      updatingHeading: "Preparing a visual update",
      failureHeading: "The visual did not complete",
      statusHeading: "Visual status",
      saving: "Saving…",
      preparing: (elapsedSeconds) => elapsedSeconds < 10
        ? "I’m preparing the visual for you…"
        : elapsedSeconds < 30
          ? "I’m building the visual step by step…"
          : "The visual is still being prepared. You can keep learning with me while it appears.",
      elapsed: (elapsedSeconds) => `Working for ${elapsedSeconds} seconds`,
      failed: "The visual could not be completed this time. You can keep chatting or request a different explanation.",
      statusUnavailable: "The visual status could not be refreshed just now.",
    },
    voice: {
      record: "Record a message",
      stop: "Stop recording and transcribe",
      cancel: "Cancel",
      requestingPermission: "Requesting microphone permission…",
      recording: (elapsed) => `Recording ${elapsed}. Stop when you are ready.`,
      transcribing: "Transcribing your recording…",
      unsupported: "Voice recording is not supported in this browser. You can keep typing.",
      unavailable: "Voice recording is unavailable right now.",
    },
    source: {
      add: "Add photo or file",
      ready: "ready to send",
      active: "in this conversation",
      remove: (filename) => `Remove ${filename}`,
      stopUsing: (filename) => `Stop using ${filename}`,
      readyPreview: (filename) => `Ready to send: ${filename}`,
      studentSource: (filename) => `Student source: ${filename}`,
      open: "Open",
      previewUnavailable: "Preview unavailable",
      loading: "Loading…",
    },
  };
}
