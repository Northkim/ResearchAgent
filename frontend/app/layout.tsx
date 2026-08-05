import type { Metadata } from "next";

import { AppShell } from "@/components/app-shell";
import { Providers } from "@/lib/providers";

import "./globals.css";

export const metadata: Metadata = {
  title: {
    default: "ReAgent Local Research",
    template: "%s · ReAgent",
  },
  description: "Package local research work for Codex and view uploaded progress.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>
        <Providers>
          <AppShell>{children}</AppShell>
        </Providers>
      </body>
    </html>
  );
}
