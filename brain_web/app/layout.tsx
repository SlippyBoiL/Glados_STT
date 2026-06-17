import "./globals.css";
import type { Metadata } from "next";
import { AppShell } from "@/components/AppShell";

export const metadata: Metadata = {
  title: "GLaDOS Swarm Command Dashboard",
  description: "Seven-agent swarm telemetry, shared brain, and facility operations",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-aperture-bg text-aperture-text antialiased">
        <AppShell>{children}</AppShell>
      </body>
    </html>
  );
}
