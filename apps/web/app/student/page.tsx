import { RoleSurface } from "@/components/role-surface";
import { SurfaceHeader } from "@/components/surface-header";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
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
          <section className="grid gap-5 md:grid-cols-3" aria-label="Student areas">
            <Card className="bg-blush">
              <CardHeader>
                <CardTitle>Math</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-sm leading-6 text-slate-600">
                  Your guided Grade 5 math space will appear here.
                </p>
              </CardContent>
            </Card>
            <Card className="bg-sky">
              <CardHeader>
                <CardTitle>Science</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-sm leading-6 text-slate-600">
                  Explore questions and explanations at your pace.
                </p>
              </CardContent>
            </Card>
            <Card className="bg-mint">
              <CardHeader>
                <CardTitle>Continue learning</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-sm leading-6 text-slate-600">
                  Your recent learning sessions will be collected here.
                </p>
              </CardContent>
            </Card>
          </section>
        </div>
      </main>
    </RoleSurface>
  );
}