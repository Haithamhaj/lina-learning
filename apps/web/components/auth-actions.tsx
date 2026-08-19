"use client";

import Link from "next/link";
import { useAuth, useClerk } from "@clerk/nextjs";

import { Button } from "@/components/ui/button";

export function AuthActions() {
  const { isLoaded, isSignedIn } = useAuth();
  const { signOut } = useClerk();

  if (!isLoaded) return null;

  if (!isSignedIn) {
    return (
      <div className="flex flex-wrap items-center gap-3">
        <Link
          href="/sign-in"
          className="inline-flex h-12 items-center justify-center rounded-full border border-slate-200 bg-white px-6 text-sm font-semibold text-ink transition-colors hover:bg-slate-50"
        >
          Sign in
        </Link>
        <Link href="/sign-up">
          <Button size="lg">Create account</Button>
        </Link>
      </div>
    );
  }

  return (
    <div className="flex flex-wrap items-center gap-3">
      <Link href="/student">
        <Button size="lg">Open learning space</Button>
      </Link>
      <button
        type="button"
        onClick={() => void signOut({ redirectUrl: "/" })}
        className="inline-flex h-12 items-center justify-center rounded-full border border-slate-200 bg-white px-6 text-sm font-semibold text-ink transition-colors hover:bg-slate-50"
      >
        Sign out
      </button>
    </div>
  );
}