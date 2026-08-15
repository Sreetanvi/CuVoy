"use client";

import { Moon, Sun } from "lucide-react";
import Link from "next/link";
import { useTheme } from "next-themes";
import { useEffect, useState } from "react";

import { SaveTripModal } from "@/components/auth/SaveTripModal";
import { Button } from "@/components/ui/button";
import { BrandLogo } from "@/components/layout/BrandLogo";
import { useAuth } from "@/context/AuthContext";

export function Header() {
  const { resolvedTheme, setTheme } = useTheme();
  const { user, loading, openAuth, signOut } = useAuth();
  const [mounted, setMounted] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  const dark = mounted && resolvedTheme === "dark";

  return (
    <header className="flex h-14 shrink-0 items-center justify-between gap-4 border-b border-border bg-background px-4">
      <Link href="/" className="flex items-center gap-2" aria-label="CuVoy home">
        <BrandLogo />
        <span className="text-sm font-semibold tracking-wide">CuVoy</span>
      </Link>
      <nav className="flex items-center gap-2">
        <Link href="/saved" className="rounded-md px-3 py-1.5 text-sm hover:bg-muted">
          Saved trips
        </Link>
        <Link
          href="/privacy"
          className="hidden rounded-md px-3 py-1.5 text-sm hover:bg-muted sm:inline"
        >
          Privacy
        </Link>
        <Link
          href="/disclaimer"
          className="hidden rounded-md px-3 py-1.5 text-sm hover:bg-muted sm:inline"
        >
          Disclaimer
        </Link>
        {loading ? (
          <span className="px-3 text-xs text-muted-foreground">…</span>
        ) : user ? (
          <div className="relative">
            <Button type="button" size="sm" variant="outline" onClick={() => setMenuOpen((open) => !open)}>
              {user.email ?? "Account"}
            </Button>
            {menuOpen ? (
              <div className="absolute right-0 z-40 mt-1 w-44 rounded-md border border-border bg-card py-1 text-sm">
                <Link
                  href="/account"
                  className="block px-3 py-2 hover:bg-muted"
                  onClick={() => setMenuOpen(false)}
                >
                  Profile settings
                </Link>
                <Link
                  href="/saved"
                  className="block px-3 py-2 hover:bg-muted"
                  onClick={() => setMenuOpen(false)}
                >
                  Saved trips
                </Link>
                <button
                  type="button"
                  className="block w-full px-3 py-2 text-left hover:bg-muted"
                  onClick={() => {
                    setMenuOpen(false);
                    void signOut();
                  }}
                >
                  Sign out
                </button>
              </div>
            ) : null}
          </div>
        ) : (
          <Button type="button" size="sm" variant="outline" onClick={() => openAuth("login")}>
            Log in
          </Button>
        )}
        <Button
          type="button"
          size="icon"
          variant="ghost"
          aria-label={dark ? "Switch to light mode" : "Switch to dark mode"}
          onClick={() => setTheme(dark ? "light" : "dark")}
        >
          {dark ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
        </Button>
      </nav>
      <SaveTripModal />
    </header>
  );
}
