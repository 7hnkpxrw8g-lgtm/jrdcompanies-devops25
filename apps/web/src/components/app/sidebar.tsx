"use client";

import {
  BarChart3,
  Banknote,
  Building2,
  CircleDollarSign,
  ClipboardCheck,
  CreditCard,
  FileText,
  Fuel,
  HardHat,
  History,
  Home,
  LayoutDashboard,
  Library,
  Network,
  Package,
  Receipt,
  Settings,
  Sparkles,
  Truck,
  Users,
  Wallet,
  Wrench,
} from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";

const NAV: { section: string; items: { name: string; href: string; icon: React.ComponentType<{ className?: string }> }[] }[] = [
  {
    section: "Overview",
    items: [
      { name: "Dashboard", href: "/app", icon: LayoutDashboard },
      { name: "AI Assistant", href: "/app/ai", icon: Sparkles },
    ],
  },
  {
    section: "Money",
    items: [
      { name: "Banking", href: "/app/banking", icon: Wallet },
      { name: "Reconciliation", href: "/app/reconciliation", icon: ClipboardCheck },
      { name: "Transactions", href: "/app/transactions", icon: Receipt },
      { name: "Ledger", href: "/app/ledger", icon: Library },
    ],
  },
  {
    section: "Commerce",
    items: [
      { name: "Invoices", href: "/app/invoices", icon: FileText },
      { name: "Bills", href: "/app/bills", icon: CreditCard },
      { name: "Customers", href: "/app/customers", icon: Users },
      { name: "Vendors", href: "/app/vendors", icon: Truck },
    ],
  },
  {
    section: "Operations",
    items: [
      { name: "Inventory", href: "/app/inventory", icon: Package },
      { name: "Fuel Ops", href: "/app/fuel", icon: Fuel },
      { name: "Repair Orders", href: "/app/repair-orders", icon: Wrench },
      { name: "Payroll", href: "/app/payroll", icon: HardHat },
    ],
  },
  {
    section: "Reports",
    items: [
      { name: "Reports", href: "/app/reports", icon: BarChart3 },
    ],
  },
  {
    section: "Platform",
    items: [
      { name: "Documents", href: "/app/documents", icon: FileText },
      { name: "Integrations", href: "/app/integrations", icon: Network },
      { name: "Audit Logs", href: "/app/audit", icon: History },
      { name: "Settings", href: "/app/settings", icon: Settings },
    ],
  },
];

export function Sidebar() {
  const pathname = usePathname();
  return (
    <aside className="hidden lg:flex w-60 shrink-0 flex-col border-r bg-card/30 backdrop-blur-sm">
      <div className="flex h-14 items-center gap-2 border-b px-4">
        <div className="h-7 w-7 rounded-md bg-primary text-primary-foreground grid place-items-center text-xs font-bold">JR</div>
        <span className="font-semibold tracking-tight">JRDbooks</span>
      </div>
      <nav className="flex-1 overflow-y-auto p-3 space-y-5">
        {NAV.map((group) => (
          <div key={group.section}>
            <div className="px-2 pb-1.5 text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
              {group.section}
            </div>
            <ul className="space-y-0.5">
              {group.items.map((item) => {
                const active = pathname === item.href || (item.href !== "/app" && pathname.startsWith(item.href));
                const Icon = item.icon;
                return (
                  <li key={item.href}>
                    <Link
                      href={item.href}
                      className={cn(
                        "flex items-center gap-2.5 rounded-md px-2 py-1.5 text-sm transition-colors",
                        active
                          ? "bg-accent text-accent-foreground font-medium"
                          : "text-muted-foreground hover:bg-accent/60 hover:text-foreground"
                      )}
                    >
                      <Icon className="h-4 w-4" />
                      {item.name}
                    </Link>
                  </li>
                );
              })}
            </ul>
          </div>
        ))}
      </nav>
      <div className="border-t p-3">
        <div className="rounded-md bg-accent/40 px-3 py-2.5 text-xs text-muted-foreground">
          <div className="flex items-center gap-1.5 font-medium text-foreground">
            <CircleDollarSign className="h-3.5 w-3.5 text-success" />
            Books are balanced
          </div>
          <p className="mt-1 leading-snug">
            Trial balance ties. Last close: <strong>Apr 30, 2026</strong>.
          </p>
        </div>
      </div>
    </aside>
  );
}
