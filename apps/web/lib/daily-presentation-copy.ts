export type DailyDirection = "ltr" | "rtl";

export type DailyPresentationCopy = {
  student: string;
  linaThinking: string;
  app: {
    daily: string;
    heading: string;
    chat: string;
    chatDescription: string;
    emptyHeading: string;
    emptyDescription: string;
    messageLabel: string;
    placeholder: string;
    thinking: string;
    send: string;
    opening: string;
    tryAgain: string;
    startNew: string;
    reload: string;
    reconnect: string;
    suggestedActions: string;
    sourceWithoutQuestion: string;
    connection: Record<"connecting" | "connected" | "reconnecting" | "error", string>;
    errors: {
      learningUnavailable: string;
      connection: string;
      workspaceRefresh: string;
      workspaceOpen: string;
      workspaceReload: string;
      workspaceNotConnected: string;
      studioSave: string;
      assetAuthentication: string;
      assetUnavailable: string;
      buildAuthentication: string;
      tutorStreamUnavailable: string;
      tutorIncomplete: string;
      tutorRejected: string;
    };
  };
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
    idleHint: string;
    sendOrClear: string;
    waitForTutor: string;
    alreadyActive: string;
    recordingStopped: string;
    permissionDenied: string;
    openFailed: string;
    noSpeechCaptured: string;
    noSpeechHeard: string;
    transcriptionFailed: string;
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
      app: {
        daily: "التعلّم اليومي",
        heading: "مساحة هادئة للتفكير بصوتٍ عالٍ.",
        chat: "محادثة التعلّم",
        chatDescription: "اسأل لينا أو اشرح ما الذي جرّبته.",
        emptyHeading: "ما الذي تحاول فهمه؟",
        emptyDescription: "ابدأ بسؤال، أو بإجابة جرّبتها، أو بشيء تريد فهمه بوضوح أكبر.",
        messageLabel: "رسالتك إلى لينا",
        placeholder: "اسأل سؤالًا أو شارك ما جرّبته",
        thinking: "لينا تفكّر…",
        send: "إرسال",
        opening: "جارٍ فتح مساحة التعلّم اليومية…",
        tryAgain: "لنحاول مرة أخرى.",
        startNew: "ابدئي جلسة جديدة",
        reload: "إعادة تحميل التعلّم اليومي",
        reconnect: "إعادة الاتصال",
        suggestedActions: "اقتراحات لينا",
        sourceWithoutQuestion: "سيُرسل الملف مع طلب المساعدة العام.",
        connection: {
          connecting: "جارٍ الاتصال بمساحة Canvas…",
          connected: "مساحة Canvas متصلة",
          reconnecting: "جارٍ إعادة الاتصال بمساحة Canvas…",
          error: "تعذر الاتصال بمساحة Canvas.",
        },
        errors: {
          learningUnavailable: "مساحة التعلّم غير متاحة مؤقتًا.",
          connection: "انقطع اتصال Canvas. جارٍ إعادة الاتصال تلقائيًا…",
          workspaceRefresh: "تعذر تحديث Canvas الآن.",
          workspaceOpen: "تعذر فتح مساحة التعلّم الآن.",
          workspaceReload: "تعذر إعادة تحميل Canvas الآن.",
          workspaceNotConnected: "Canvas غير متصلة الآن.",
          studioSave: "تعذر حفظ هذا التفاعل. أعدنا تحميل الحالة الحالية.",
          assetAuthentication: "تعذر التحقق من صلاحية الملف الآن.",
          assetUnavailable: "الملف البصري غير متاح الآن.",
          buildAuthentication: "تعذر التحقق من صلاحية الرسم التفاعلي الآن.",
          tutorStreamUnavailable: "تعذر بدء رد لينا الآن.",
          tutorIncomplete: "لم يكتمل رد لينا. يمكنكِ المحاولة مرة أخرى.",
          tutorRejected: "لم أستطع إكمال هذا الرد بأمان. جرّبي مرة أخرى أو تابعي بالسؤال نفسه.",
        },
      },
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
        idleHint: "اكتبي رسالة أو سجّليها، ثم راجعيها قبل الإرسال.",
        sendOrClear: "أرسلي الرسالة المكتوبة أو امسحيها قبل التسجيل.",
        waitForTutor: "انتظري رد لينا قبل التسجيل.",
        alreadyActive: "الإدخال الصوتي يعمل الآن.",
        recordingStopped: "توقف التسجيل بشكل غير متوقع. حاولي مرة أخرى.",
        permissionDenied: "رُفض إذن الميكروفون. يمكنكِ متابعة الكتابة أو السماح بالوصول ثم المحاولة.",
        openFailed: "تعذر فتح الميكروفون. يمكنكِ متابعة الكتابة والمحاولة لاحقًا.",
        noSpeechCaptured: "لم يُلتقط صوت. سجّلي مرة أخرى.",
        noSpeechHeard: "لم نسمع كلامًا واضحًا. سجّلي مرة أخرى.",
        transcriptionFailed: "تعذر تحويل التسجيل إلى نص. حاولي مرة أخرى.",
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
    app: {
      daily: "Daily learning",
      heading: "A calm place to think out loud.",
      chat: "Learning Chat",
      chatDescription: "Ask Lina a question or explain what you tried.",
      emptyHeading: "What are you working through?",
      emptyDescription: "Start with a question, an answer you tried, or something you would like to understand more clearly.",
      messageLabel: "Your message for Lina",
      placeholder: "Ask a question or share what you tried",
      thinking: "Lina is thinking…",
      send: "Send",
      opening: "Opening your Daily learning space…",
      tryAgain: "Let’s try again.",
      startNew: "Start a new session",
      reload: "Reload Daily",
      reconnect: "Reconnect",
      suggestedActions: "Tutor suggested actions",
      sourceWithoutQuestion: "The file will be sent with a general request for help.",
      connection: {
        connecting: "Connecting to Canvas…",
        connected: "Canvas connected",
        reconnecting: "Reconnecting to Canvas…",
        error: "Canvas connection is unavailable.",
      },
      errors: {
        learningUnavailable: "This learning space is temporarily unavailable.",
        connection: "Canvas connection was interrupted. Reconnecting automatically…",
        workspaceRefresh: "Canvas could not be refreshed just now.",
        workspaceOpen: "This learning space could not be opened just now.",
        workspaceReload: "Canvas could not be reloaded just now.",
        workspaceNotConnected: "Canvas is not connected right now.",
        studioSave: "That interaction could not be saved. The current state was reloaded.",
        assetAuthentication: "The visual file could not be authorized just now.",
        assetUnavailable: "The visual file is unavailable right now.",
        buildAuthentication: "The interactive visual could not be authorized just now.",
        tutorStreamUnavailable: "Lina’s response could not start just now.",
        tutorIncomplete: "Lina’s response did not finish. You can try again.",
        tutorRejected: "I could not complete that response safely. Try again or continue with the same question.",
      },
    },
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
      idleHint: "Type a message or record one, then review it before sending.",
      sendOrClear: "Send or clear your typed message before recording.",
      waitForTutor: "Wait for Lina before recording.",
      alreadyActive: "Voice input is already active.",
      recordingStopped: "Voice recording stopped unexpectedly. Please try again.",
      permissionDenied: "Microphone permission was denied. You can keep typing or allow access and try again.",
      openFailed: "The microphone could not be opened. You can keep typing and try again.",
      noSpeechCaptured: "No speech was captured. Please record again.",
      noSpeechHeard: "We could not hear any speech. Please record again.",
      transcriptionFailed: "The recording could not be transcribed. Please try again.",
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
