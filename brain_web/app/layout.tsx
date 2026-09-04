import "./globals.css";
import type { Metadata } from "next";
import { AppShell } from "@/components/AppShell";

export const metadata: Metadata = {
  title: "GLaDOS Neural Observation Room",
  description:
    "Aperture Science administrative terminal — live firing brain, system state, internal monologue",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-[#00050b] text-[#00F0FF] antialiased">
        <AppShell>{children}</AppShell>
      </body>
    </html>
  );
}
