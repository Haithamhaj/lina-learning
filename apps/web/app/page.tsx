import { AuthActions } from "@/components/auth-actions";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { publicConfig } from "@/lib/public-config";

const foundationAreas = [
  {
    title: "Student experience",
    description: "A calm, child-friendly surface for future learning flows.",
    toneClass: "bg-blush",
  },
  {
    title: "Parent control",
    description: "A separate, inspectable area for future oversight and settings.",
    toneClass: "bg-sky",
  },
  {
    title: "Modular foundation",
    description: "Web and API shells ready for the approved implementation sequence.",
    toneClass: "bg-mint",
  },
];

export default function HomePage() {
  return (
    <main className="min-h-screen bg-[#f5f7fb] px-5 py-8 text-ink sm:px-8 lg:px-12">
      <div className="mx-auto flex max-w-6xl flex-col gap-12">
        <header className="flex flex-col gap-6 border-b border-slate-200 pb-10 sm:flex-row sm:items-end sm:justify-between">
          <div className="max-w-2xl">
            <p className="mb-3 text-sm font-bold uppercase tracking-[0.18em] text-lavender">
              Lina Personal Learning System
            </p>
            <h1 className="text-4xl font-semibold tracking-tight sm:text-6xl">
              A thoughtful foundation for learning.
            </h1>
            <p className="mt-5 max-w-xl text-lg leading-8 text-slate-600">
              The Phase 0 application shell is ready. Product features will be
              added one verified task at a time.
            </p>
            <p className="mt-4 text-sm font-medium text-slate-500">
              Runtime: {publicConfig.appEnv}
            </p>
          </div>
          <AuthActions />
        </header>

        <section aria-labelledby="foundation-heading">
          <div className="mb-5">
            <p className="text-sm font-semibold text-slate-500">CURRENT MILESTONE</p>
            <h2 id="foundation-heading" className="mt-1 text-2xl font-semibold">
              Phase 0 · Repository & runtime foundation
            </h2>
          </div>
          <div className="grid gap-5 md:grid-cols-3">
            {foundationAreas.map((area) => (
              <Card key={area.title} className={area.toneClass}>
                <CardHeader>
                  <CardTitle>{area.title}</CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-sm leading-6 text-slate-600">{area.description}</p>
                </CardContent>
              </Card>
            ))}
          </div>
        </section>

        <section className="rounded-3xl bg-white p-7 shadow-soft sm:p-10" aria-labelledby="principles-heading">
          <p className="text-sm font-semibold text-lavender">GOVERNED BY THE STARTER PACK</p>
          <h2 id="principles-heading" className="mt-2 text-2xl font-semibold">
            Simple on the surface. Traceable underneath.
          </h2>
          <div className="mt-7 grid gap-6 text-sm leading-6 text-slate-600 sm:grid-cols-3">
            <p>
              <strong className="text-ink">Evidence first.</strong> Learner
              understanding will be derived from preserved interaction history.
            </p>
            <p>
              <strong className="text-ink">Current behavior matters.</strong>{" "}
              Future personalization remains advisory, never a fixed label.
            </p>
            <p>
              <strong className="text-ink">Build in sequence.</strong> Later
              phases stay blocked until the real learning loop is verified.
            </p>
          </div>
        </section>
      </div>
    </main>
  );
}