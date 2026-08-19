import Link from "next/link";

import { SignOutButtonControl } from "@/components/sign-out-button";

export function SurfaceHeader({
  eyebrow,
  title,
  description,
}: {
  eyebrow: string;
  title: string;
  description: string;
}) {
  return (
    <header className="flex flex-col gap-6 border-b border-slate-200 pb-8 sm:flex-row sm:items-end sm:justify-between">
      <div>
        <Link
          href="/"
          className="text-sm font-bold uppercase tracking-[0.18em] text-lavender"
        >
          Lina Personal Learning System
        </Link>
        <p className="mt-8 text-sm font-semibold uppercase tracking-[0.14em] text-slate-500">
          {eyebrow}
        </p>
        <h1 className="mt-2 text-4xl font-semibold tracking-tight text-ink sm:text-5xl">
          {title}
        </h1>
        <p className="mt-4 max-w-2xl text-lg leading-8 text-slate-600">
          {description}
        </p>
      </div>
      <SignOutButtonControl />
    </header>
  );
}