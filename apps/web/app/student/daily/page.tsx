import { DailyStudentApp } from "@/components/daily-student/daily-student-app";
import { RoleSurface } from "@/components/role-surface";
import { USER_ROLES } from "@/lib/auth/roles";

export default function DailyStudentPage() {
  return (
    <RoleSurface requiredRole={USER_ROLES.STUDENT} redirectPath="/parent">
      <DailyStudentApp />
    </RoleSurface>
  );
}
