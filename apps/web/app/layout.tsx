import type { Metadata } from "next";

import { Providers } from "@/components/providers";

import "./globals.css";

export const metadata: Metadata = {
  title: "Lina Learning",
  description: "A thoughtful foundation for learning.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  const publishableKey = process.env.CLERK_PUBLISHABLE_KEY;
  const proxyUrl = process.env.CLERK_PROXY_URL;

  return (
    <html lang="en">
      <body>
        <Providers publishableKey={publishableKey} proxyUrl={proxyUrl}>
          {children}
        </Providers>
      </body>
    </html>
  );
}
