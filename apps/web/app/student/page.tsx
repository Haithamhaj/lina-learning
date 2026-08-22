import { RoleSurface } from "@/components/role-surface";
import { StudentMathSession } from "@/components/student-math-session";
import { SurfaceHeader } from "@/components/surface-header";
import { USER_ROLES } from "@/lib/auth/roles";

export default function StudentPage() {
  return (
    <RoleSurface
      requiredRole={USER_ROLES.STUDENT}
      redirectPath="/parent"
    >
      <main className="min-h-screen bg-[linear-gradient(135deg,#fbf9ff_0%,#f4fbfa_52%,#fff8ef_100%)] px-4 py-6 text-ink sm:px-8 sm:py-10 lg:px-12">
        <div className="mx-auto flex max-w-5xl flex-col gap-8 sm:gap-10">
          <SurfaceHeader
            eyebrow="Math with Tutor"
            title="Let’s work it out together."
            description="Ask a question, share an answer, or show what you tried."
          />
          <StudentMathSession />
        </div>
      </main>
    </RoleSurface>
  );
}
