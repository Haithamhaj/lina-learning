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
      <main className="min-h-screen bg-[#f5f7fb] px-5 py-8 text-ink sm:px-8 lg:px-12">
        <div className="mx-auto flex max-w-6xl flex-col gap-10">
          <SurfaceHeader
            eyebrow="Student learning space"
            title="A calm place to keep learning."
            description="Ask questions, work through ideas, and keep the focus on learning rather than analytics."
          />
          <StudentMathSession />
        </div>
      </main>
    </RoleSurface>
  );
}
