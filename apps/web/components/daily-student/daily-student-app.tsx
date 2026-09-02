"use client";

import { DailyLearningChat } from "@/components/daily-student/daily-learning-chat";
import { DailyLearningWorkspace } from "@/components/daily-student/daily-learning-workspace";
import { useDailyTutorSession } from "@/components/daily-student/use-daily-tutor-session";

export function DailyStudentApp() {
  const session = useDailyTutorSession();

  return (
    <main className="min-h-screen overflow-hidden bg-[#f4f4f1] px-3 py-3 text-[#17253b] sm:px-5 sm:py-5 lg:px-7 lg:py-6">
      <div aria-hidden="true" className="pointer-events-none fixed inset-0 -z-10 overflow-hidden">
        <div className="absolute -left-44 top-8 size-[38rem] rounded-full bg-[#d9d2ff]/55 blur-3xl" />
        <div className="absolute -right-36 bottom-[-8rem] size-[42rem] rounded-full bg-[#c9f0df]/50 blur-3xl" />
        <div className="absolute left-[47%] top-[12%] size-[26rem] rounded-full border border-white/70" />
        <div className="absolute inset-x-0 top-0 h-px bg-white/90" />
      </div>

      <div className="mx-auto max-w-[1540px]">
        <header className="flex items-center justify-between gap-4 px-2 pb-4 sm:px-3 sm:pb-5 lg:pb-6">
          <div className="flex items-center gap-3">
            <span aria-hidden="true" className="grid size-11 place-items-center rounded-[1.15rem] bg-[#0d3042] text-lg text-[#dff8ef] shadow-[0_15px_28px_-14px_rgba(10,38,54,0.8)]">✦</span>
            <div>
              <p className="text-base font-semibold tracking-[-0.04em] text-[#102d45] sm:text-lg">Lina Learning</p>
              <p className="text-xs font-medium text-[#687787] sm:text-sm">Your daily learning studio</p>
            </div>
          </div>
          <div className="hidden items-center gap-2 rounded-full border border-white/80 bg-white/60 px-3 py-1.5 text-xs font-semibold text-[#49606e] shadow-[0_12px_26px_-20px_rgba(26,55,72,0.7)] backdrop-blur sm:flex">
            <span aria-hidden="true" className="size-1.5 rounded-full bg-[#56a98d]" />
            Daily Studio
          </div>
        </header>

        <div className="grid gap-4 lg:min-h-[calc(100dvh-10rem)] lg:grid-cols-[minmax(23rem,0.82fr)_minmax(0,1.45fr)] lg:gap-6">
          <DailyLearningChat {...session} />
          <DailyLearningWorkspace {...session} />
        </div>
      </div>
    </main>
  );
}
