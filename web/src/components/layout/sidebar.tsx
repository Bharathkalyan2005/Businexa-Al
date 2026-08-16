"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  BarChart3,
  FileText,
  LayoutDashboard,
  Settings,
  Upload,
} from "lucide-react";

import { cn } from "@/lib/utils";

type SidebarProps = {
  businessId: string;
  businessName: string;
};

const navItems = [
  { label: "Dashboard", href: "", icon: LayoutDashboard },
  { label: "Upload", href: "/upload", icon: Upload },
  { label: "Reports", href: "/reports", icon: FileText },
  { label: "Settings", href: "/settings", icon: Settings },
] as const;

export function Sidebar({ businessId, businessName }: SidebarProps) {
  const pathname = usePathname();
  const basePath = `/dashboard/${businessId}`;

  return (
    <aside className="flex w-64 shrink-0 flex-col border-r border-border bg-sidebar text-sidebar-foreground">
      <div className="border-b border-sidebar-border px-6 py-5">
        <div className="flex items-center gap-2">
          <BarChart3 className="size-5 text-sidebar-primary" />
          <span className="text-lg font-semibold tracking-tight">Businexa AI</span>
        </div>
        <p className="mt-2 truncate text-sm text-muted-foreground">{businessName}</p>
      </div>

      <nav className="flex flex-1 flex-col gap-1 p-4">
        {navItems.map((item) => {
          const href = `${basePath}${item.href}`;
          const isActive =
            item.href === ""
              ? pathname === basePath
              : pathname.startsWith(href);
          const Icon = item.icon;

          return (
            <Link
              key={item.label}
              href={href}
              className={cn(
                "flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors",
                isActive
                  ? "bg-sidebar-accent text-sidebar-accent-foreground"
                  : "text-muted-foreground hover:bg-sidebar-accent/60 hover:text-sidebar-accent-foreground",
              )}
            >
              <Icon className="size-4" />
              {item.label}
            </Link>
          );
        })}
      </nav>
    </aside>
  );
}
