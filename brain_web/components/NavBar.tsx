"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const links = [
  { href: "/hud/", label: "Command Center" },
  { href: "/", label: "Live Mind" },
  { href: "/memory/", label: "Memory" },
  { href: "/skills/", label: "Skills" },
  { href: "/intents/", label: "Intents" },
  { href: "/monitor/", label: "Monitor" },
];

export function NavBar() {
  const path = usePathname();

  return (
    <header className="border-b border-aperture-border bg-aperture-panel/80 backdrop-blur">
      <div className="mx-auto flex max-w-7xl items-center justify-between px-4 py-3">
        <div>
          <p className="text-xs uppercase tracking-[0.25em] text-aperture-muted">
            Aperture Science
          </p>
          <h1 className="text-lg font-semibold text-aperture-orange">
            GLaDOS Brain Observatory
          </h1>
        </div>
        <nav className="flex flex-wrap gap-1">
          {links.map((l) => {
            const active =
              l.href === "/"
                ? path === "/" || path === ""
                : path.startsWith(l.href.replace(/\/$/, ""));
            return (
              <Link
                key={l.href}
                href={l.href}
                className={`rounded px-3 py-1.5 text-sm transition ${
                  active
                    ? "bg-aperture-orange/20 text-aperture-orange"
                    : "text-aperture-muted hover:text-aperture-text"
                }`}
              >
                {l.label}
              </Link>
            );
          })}
        </nav>
      </div>
    </header>
  );
}
