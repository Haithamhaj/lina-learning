"use client";

import { useAuth, useUser } from "@clerk/nextjs";
import { useRouter } from "next/navigation";
import { useEffect, type ReactNode } from "react";

import { USER_ROLES, roleFromClaims, type UserRole } from "@/lib/auth/roles";

export function RoleSurface({
  requiredRole,
  redirectPath,
  children,
}: {
  requiredRole: UserRole;
  redirectPath: string;
  children: ReactNode;
}) {
  const { isLoaded, isSignedIn, sessionClaims } = useAuth();
  const { isLoaded: isUserLoaded, user } = useUser();
  const router = useRouter();
  const role = roleFromClaims({
    ...(sessionClaims ?? {}),
    public_metadata: user?.publicMetadata,
  });

  useEffect(() => {
    if (!isLoaded || !isUserLoaded) return;
    if (!isSignedIn) {
      router.replace("/sign-in");
      return;
    }
    if (role !== requiredRole) {
      router.replace(redirectPath);
    }
  }, [
    isLoaded,
    isUserLoaded,
    isSignedIn,
    role,
    requiredRole,
    redirectPath,
    router,
  ]);

  if (!isLoaded || !isUserLoaded || !isSignedIn || role !== requiredRole) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-[#f5f7fb] px-5 text-sm text-slate-500">
        Checking your Lina space…
      </main>
    );
  }

  return <>{children}</>;
}
