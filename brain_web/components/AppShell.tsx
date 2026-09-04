"use client";

import { usePathname } from "next/navigation";
import { NavBar } from "./NavBar";

export function AppShell({ children }: { children: React.ReactNode }) {
  const path = usePathname() || "";
  const isImmersive =
    path === "/" || path.startsWith("/hud") || path.startsWith("/observatory");

  if (isImmersive) {
    return <>{children}</>;
  }

  return (
    <>
      <NavBar />
      <main className="mx-auto max-w-7xl px-4 py-6">{children}</main>
    </>
  );
}
