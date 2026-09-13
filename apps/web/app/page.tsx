import { AuthActions } from "@/components/auth-actions";

export default function HomePage() {
  return (
    <main className="flex min-h-screen items-center justify-center bg-[#f5f7fb] px-5 py-12 text-ink">
      <section className="w-full max-w-3xl rounded-[2rem] bg-white px-7 py-14 text-center shadow-soft sm:px-12 sm:py-20">
        <p className="text-sm font-bold uppercase tracking-[0.18em] text-lavender">
          Welcome to
        </p>
        <h1 className="mt-4 text-4xl font-semibold tracking-tight sm:text-6xl">
          Lina Personal Learning System
        </h1>
        <p className="mx-auto mt-6 max-w-xl text-lg leading-8 text-slate-600 sm:text-xl">
          Your personal space to learn, understand, and explore with confidence.
        </p>
        <div className="mt-10 flex justify-center">
          <AuthActions />
        </div>
      </section>
    </main>
  );
}
