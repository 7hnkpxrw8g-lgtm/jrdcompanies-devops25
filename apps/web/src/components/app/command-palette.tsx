"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import {
  BarChart3,
  Banknote,
  ClipboardCheck,
  CreditCard,
  FileText,
  Fuel,
  HardHat,
  Home,
  LayoutDashboard,
  Library,
  Network,
  Package,
  Receipt,
  Search,
  Settings,
  Sparkles,
  Truck,
  Users,
  Wallet,
  Wrench,
} from "lucide-react";

const NAV_ITEMS: { name: string; href: string; icon: React.ComponentType<{ className?: string }>; keywords?: string }[] = [
  { name: "Dashboard", href: "/app", icon: LayoutDashboard, keywords: "home overview kpi" },
  { name: "Banking", href: "/app/banking", icon: Wallet, keywords: "bank accounts feeds" },
  { name: "Reconciliation", href: "/app/reconciliation", icon: ClipboardCheck, keywords: "match transactions" },
  { name: "Transactions / Journals", href: "/app/transactions", icon: Receipt, keywords: "journal entry" },
  { name: "New journal", href: "/app/transactions/new", icon: Receipt, keywords: "create entry post" },
  { name: "Ledger", href: "/app/ledger", icon: Library, keywords: "general ledger gl" },
  { name: "Reports", href: "/app/reports", icon: BarChart3, keywords: "p&l balance sheet" },
  { name: "Invoices", href: "/app/invoices", icon: FileText, keywords: "ar receivable" },
  { name: "New invoice", href: "/app/invoices/new", icon: FileText, keywords: "create invoice" },
  { name: "Bills", href: "/app/bills", icon: CreditCard, keywords: "ap payable" },
  { name: "Customers", href: "/app/customers", icon: Users },
  { name: "Vendors", href: "/app/vendors", icon: Truck },
  { name: "Inventory", href: "/app/inventory", icon: Package, keywords: "stock skus" },
  { name: "Fuel ops", href: "/app/fuel", icon: Fuel, keywords: "tank dispense variance" },
  { name: "Repair orders", href: "/app/repair-orders", icon: Wrench, keywords: "ro shop" },
  { name: "Payroll", href: "/app/payroll", icon: HardHat },
  { name: "AI assistant", href: "/app/ai", icon: Sparkles },
  { name: "Integrations", href: "/app/integrations", icon: Network, keywords: "plaid stripe square" },
  { name: "Audit logs", href: "/app/audit", icon: FileText },
  { name: "Settings", href: "/app/settings", icon: Settings },
];

export function CommandPalette() {
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [focusIdx, setFocusIdx] = useState(0);

  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setOpen((v) => !v);
        setQuery("");
        setFocusIdx(0);
      }
      if (open && e.key === "Escape") {
        setOpen(false);
      }
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open]);

  const matches = NAV_ITEMS.filter((item) => {
    if (!query) return true;
    const haystack = `${item.name} ${item.keywords ?? ""}`.toLowerCase();
    return haystack.includes(query.toLowerCase());
  });

  function go(href: string) {
    setOpen(false);
    router.push(href);
  }

  function onKey(e: React.KeyboardEvent) {
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setFocusIdx((i) => Math.min(matches.length - 1, i + 1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setFocusIdx((i) => Math.max(0, i - 1));
    } else if (e.key === "Enter") {
      e.preventDefault();
      const target = matches[focusIdx];
      if (target) go(target.href);
    }
  }

  if (!open) return null;
  return (
    <div
      className="fixed inset-0 z-50 grid place-items-start justify-center bg-background/80 backdrop-blur-sm pt-[15vh]"
      onClick={() => setOpen(false)}
    >
      <div
        className="w-full max-w-xl rounded-lg border bg-card shadow-2xl overflow-hidden animate-slide-up"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center gap-2 border-b px-3">
          <Search className="h-4 w-4 text-muted-foreground" />
          <input
            autoFocus
            value={query}
            onChange={(e) => {
              setQuery(e.target.value);
              setFocusIdx(0);
            }}
            onKeyDown={onKey}
            placeholder="Search or jump to…"
            className="h-12 flex-1 bg-transparent outline-none placeholder:text-muted-foreground"
          />
          <kbd className="text-[10px] text-muted-foreground border rounded px-1.5 py-0.5">ESC</kbd>
        </div>
        <div className="max-h-80 overflow-y-auto p-1.5">
          {matches.length === 0 ? (
            <div className="px-3 py-6 text-center text-sm text-muted-foreground">No results.</div>
          ) : (
            matches.map((item, i) => {
              const Icon = item.icon;
              return (
                <button
                  key={item.href}
                  onClick={() => go(item.href)}
                  onMouseEnter={() => setFocusIdx(i)}
                  className={`flex items-center w-full gap-2.5 rounded-md px-3 py-2 text-left text-sm ${
                    focusIdx === i ? "bg-accent text-accent-foreground" : "hover:bg-accent/60"
                  }`}
                >
                  <Icon className="h-4 w-4 text-muted-foreground" />
                  <span className="font-medium">{item.name}</span>
                  <span className="ml-auto text-xs text-muted-foreground">{item.href}</span>
                </button>
              );
            })
          )}
        </div>
      </div>
    </div>
  );
}
