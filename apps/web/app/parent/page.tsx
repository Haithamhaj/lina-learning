import { RoleSurface } from "@/components/role-surface";
import { SurfaceHeader } from "@/components/surface-header";
import { ContentUpload } from "@/components/content-upload";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { USER_ROLES } from "@/lib/auth/roles";

export default function ParentPage() {
  return (
    <RoleSurface
      requiredRole={USER_ROLES.PARENT_ADMIN}
      redirectPath="/student"
    >
      <main className="min-h-screen bg-[#f5f7fb] px-5 py-8 text-ink sm:px-8 lg:px-12">
        <div className="mx-auto flex max-w-6xl flex-col gap-10">
          <SurfaceHeader
            eyebrow="Parent control surface"
            title="Understand the learning environment."
            description="A separate space for oversight and settings, without leaking parent analytics into the student experience."
          />
          <section className="grid gap-5 md:grid-cols-3" aria-label="Parent areas">
            <Card className="bg-sky">
              <CardHeader>
                <CardTitle>Student overview</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-sm leading-6 text-slate-600">
                  Inspect learning context and important evidence.
                </p>
              </CardContent>
            </Card>
            <Card className="bg-mint">
              <CardHeader>
                <CardTitle>Learning environment</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-sm leading-6 text-slate-600">Preserve a Grade book before it is processed into learning context.</p>
              </CardContent>
            </Card>
            <Card className="bg-blush">
              <CardHeader>
                <CardTitle>Boundaries</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-sm leading-6 text-slate-600">
                  Safety and learning boundary controls remain protected by policy.
                </p>
              </CardContent>
            </Card>
          </section>
          <Card>
            <CardHeader>
              <CardTitle>Add a Grade 5 Math book</CardTitle>
            </CardHeader>
            <CardContent>
              <ContentUpload />
            </CardContent>
          </Card>
        </div>
      </main>
    </RoleSurface>
  );
}
