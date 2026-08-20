"use client";

import { ClerkProvider } from "@clerk/nextjs";
import { shadcn } from "@clerk/themes";
import type { ReactNode } from "react";
import { usePathname } from "next/navigation";

const appearance = {
  baseTheme: shadcn,
  variables: {
    colorPrimary: "#6658d3",
    colorForeground: "#182033",
    colorMutedForeground: "#64748b",
    colorBackground: "#ffffff",
    colorInput: "#ffffff",
    colorInputForeground: "#182033",
    colorNeutral: "#e2e8f0",
    fontFamily: "Arial, Helvetica, sans-serif",
    borderRadius: "1rem",
  },
  elements: {
    cardBox: "w-full max-w-[440px] rounded-3xl bg-white shadow-soft",
    card: "border-0 shadow-none",
    headerTitle: "text-ink",
    headerSubtitle: "text-slate-600",
    formButtonPrimary: "bg-ink hover:bg-slate-700",
    footerActionLink: "text-lavender",
    formFieldInput: "rounded-xl",
    socialButtonsBlockButton: "rounded-xl",
  },
  options: {
    logoImageUrl: "/logo.svg",
    logoLinkUrl: "/",
    logoPlacement: "inside" as const,
    socialButtonsPlacement: "top" as const,
  },
};

export function Providers({
  children,
  publishableKey,
}: {
  children: ReactNode;
  publishableKey?: string;
}) {
  const pathname = usePathname();
  const isDevelopmentDemoRequest =
    process.env.NODE_ENV === "development" &&
    (pathname === "/demo" || pathname === "/icon.svg");

  if (!publishableKey && isDevelopmentDemoRequest) {
    return <>{children}</>;
  }

  if (!publishableKey) {
    throw new Error("CLERK_PUBLISHABLE_KEY is required for the web app.");
  }

  return (
    <ClerkProvider
      publishableKey={publishableKey}
      appearance={appearance}
      signInUrl="/sign-in"
      signUpUrl="/sign-up"
      localization={{
        signIn: {
          start: {
            title: "Welcome back to Lina",
            subtitle: "Sign in to open your learning space.",
          },
        },
        signUp: {
          start: {
            title: "Create a Lina account",
            subtitle: "Start a calm, evidence-grounded learning journey.",
          },
        },
      }}
    >
      {children}
    </ClerkProvider>
  );
}
