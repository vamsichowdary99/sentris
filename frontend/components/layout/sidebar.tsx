"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { FolderOpen, LayoutDashboard, LogOut, ScanSearch, ShieldAlert } from "lucide-react";
import { cn } from "@/lib/utils";
import { logout } from "@/lib/auth";
import { useAuthStore } from "@/lib/auth-store";
import { useSidebarStore } from "@/lib/sidebar-store";

const NAV_ITEMS = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/alerts", label: "Alerts", icon: ShieldAlert },
  { href: "/investigate", label: "Investigate", icon: ScanSearch },
  { href: "/cases", label: "Cases", icon: FolderOpen },
];

export function Sidebar() {
  const pathname = usePathname();
  const router = useRouter();
  const isOpen = useSidebarStore((s) => s.isOpen);
  const close = useSidebarStore((s) => s.close);
  const user = useAuthStore((s) => s.user);
  const roles = useAuthStore((s) => s.roles);

  async function handleLogout() {
    await logout();
    router.push("/login");
  }

  return (
    <>
      {isOpen && (
        <div
          className="fixed inset-0 z-30 bg-void/70 lg:hidden"
          onClick={close}
          aria-hidden
        />
      )}
      <aside
        className={cn(
          "fixed inset-y-0 left-0 z-40 flex w-60 shrink-0 -translate-x-full flex-col border-r border-line bg-surface transition-transform duration-200 lg:static lg:translate-x-0",
          isOpen && "translate-x-0",
        )}
      >
        <Link href="/dashboard" className="flex items-center gap-2 px-5 py-5" onClick={close}>
          <span className="grid grid-cols-2 gap-0.5">
            <span className="h-1.5 w-1.5 rounded-[1px] bg-cyan" />
            <span className="h-1.5 w-1.5 rounded-[1px] bg-amber" />
            <span className="h-1.5 w-1.5 rounded-[1px] bg-amber" />
            <span className="h-1.5 w-1.5 rounded-[1px] bg-cyan" />
          </span>
          <span className="font-display text-xl tracking-tight text-paper">Sentris</span>
        </Link>

        <nav className="flex flex-col gap-0.5 px-3 py-2">
          {NAV_ITEMS.map((item) => {
            const active = pathname?.startsWith(item.href);
            const Icon = item.icon;
            return (
              <Link
                key={item.href}
                href={item.href}
                onClick={close}
                className={cn(
                  "group relative flex items-center gap-3 rounded-md px-3 py-2 text-sm transition-colors",
                  active ? "text-paper" : "text-mist hover:text-paper",
                )}
              >
                {active && (
                  <span className="absolute left-0 top-1/2 h-4 w-0.5 -translate-y-1/2 rounded-full bg-cyan" />
                )}
                <Icon
                  size={17}
                  strokeWidth={2}
                  className={active ? "text-cyan" : "text-mist group-hover:text-paper"}
                />
                {item.label}
              </Link>
            );
          })}
        </nav>

        <div className="mt-auto flex items-center gap-2.5 border-t border-line px-5 py-4">
          <span className="relative flex h-2 w-2 shrink-0">
            <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-cyan opacity-40" />
            <span className="relative inline-flex h-2 w-2 rounded-full bg-cyan" />
          </span>
          <div className="min-w-0 flex-1 text-xs">
            <div className="truncate text-paper">{user?.full_name ?? "Analyst"}</div>
            <div className="truncate font-mono text-[11px] text-mist">
              {roles[0] ?? "no role"}
            </div>
          </div>
          <button
            onClick={handleLogout}
            aria-label="Sign out"
            className="shrink-0 rounded-md p-1.5 text-mist hover:bg-surface-raised hover:text-threat"
          >
            <LogOut size={15} />
          </button>
        </div>
      </aside>
    </>
  );
}
