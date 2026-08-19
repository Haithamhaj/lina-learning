"use client";

import { useClerk } from "@clerk/nextjs";

export function SignOutButtonControl() {
  const { signOut } = useClerk();

  return (
    <button
      type="button"
      onClick={() => void signOut({ redirectUrl: "/" })}
      className="inline-flex h-10 items-center justify-center rounded-full border border-slate-200 bg-white px-5 text-sm font-semibold text-ink transition-colors hover:bg-slate-50"
    >
      Sign out
    </button>
  );
}