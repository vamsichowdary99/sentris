"use client";

import { Menu } from "lucide-react";
import { useSidebarStore } from "@/lib/sidebar-store";

export function Topbar({
  title,
  description,
  action,
}: {
  title: string;
  description?: string;
  action?: React.ReactNode;
}) {
  const toggle = useSidebarStore((s) => s.toggle);

  return (
    <header className="flex flex-wrap items-center justify-between gap-x-4 gap-y-3 border-b border-line px-5 py-5 sm:px-8">
      <div className="flex items-center gap-3 min-w-0">
        <button
          onClick={toggle}
          className="shrink-0 rounded-md border border-line p-1.5 text-mist hover:text-paper lg:hidden"
          aria-label="Toggle navigation"
        >
          <Menu size={18} />
        </button>
        <div className="min-w-0">
          <h1 className="truncate font-display text-2xl text-paper">{title}</h1>
          {description && <p className="mt-0.5 text-sm text-mist">{description}</p>}
        </div>
      </div>
      {action}
    </header>
  );
}
