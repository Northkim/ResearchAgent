import type { Metadata } from "next";

import { AppShell } from "@/components/app-shell";
import { Providers } from "@/lib/providers";

import "./globals.css";

export const metadata: Metadata = {
  title: {
    default: "ReAgent Research Operations",
    template: "%s · ReAgent",
  },
  description: "Launch, monitor, and govern durable research agent workflows.",
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
