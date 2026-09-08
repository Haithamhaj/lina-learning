import { DailyStudentApp } from "@/components/daily-student/daily-student-app";
import { RoleSurface } from "@/components/role-surface";
import { USER_ROLES } from "@/lib/auth/roles";
import "@/lib/studio/visual-toolbelt/toolbelt.css";

export default function DailyStudentPage() {
  return (
    <RoleSurface requiredRole={USER_ROLES.STUDENT} redirectPath="/parent">
      <DailyStudentApp />
    </RoleSurface>
  );
}
