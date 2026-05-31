"use client";

import { Bell, LogOut, Search } from "lucide-react";
import { ThemeToggle } from "./theme-toggle";
import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { useQuery } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { apiClient, setToken } from "@/lib/api";
import { useAppStore } from "@/lib/store";
import type { Entity } from "@/lib/types";

export function Topbar() {
  const router = useRouter();
  const { user, entities, setEntities, activeEntityId, setActiveEntityId, setUser } = useAppStore();

  const { data } = useQuery({
    queryKey: ["entities"],
    queryFn: () => apiClient.get<Entity[]>("/entities"),
  });

  useEffect(() => {
    if (data) setEntities(data);
  }, [data, setEntities]);

  function logout() {
    setToken(null);
    setUser(null);
    router.push("/login");
  }

  return (
    <header className="flex h-14 items-center justify-between gap-4 border-b bg-background/80 backdrop-blur-md px-4 lg:px-6 sticky top-0 z-10">
      <div className="flex items-center gap-3 flex-1 max-w-2xl">
        <div className="relative flex-1">
          <Search className="absolute left-2.5 top-2.5 h-3.5 w-3.5 text-muted-foreground" />
          <Input
            placeholder="Search invoices, customers, accounts, journals…"
            className="pl-8 h-9 bg-accent/30 border-transparent focus:bg-background"
          />
          <kbd className="pointer-events-none absolute right-2 top-2 hidden h-5 select-none items-center gap-1 rounded border bg-background px-1.5 font-mono text-[10px] text-muted-foreground sm:flex">
            ⌘K
          </kbd>
        </div>
      </div>

      <div className="flex items-center gap-3">
        {entities.length > 0 ? (
          <select
            value={activeEntityId ?? ""}
            onChange={(e) => setActiveEntityId(e.target.value || null)}
            className="h-9 rounded-md border bg-background px-3 text-sm font-medium focus-ring"
          >
            {entities.map((entity) => (
              <option key={entity.id} value={entity.id}>
                {entity.code} — {entity.name}
              </option>
            ))}
          </select>
        ) : null}

        <ThemeToggle />

        <Button variant="ghost" size="icon" aria-label="Notifications">
          <Bell className="h-4 w-4" />
        </Button>

        <div className="flex items-center gap-2 rounded-md border bg-card px-2.5 py-1">
          <div className="h-7 w-7 rounded-full bg-primary text-primary-foreground grid place-items-center text-xs font-semibold">
            {(user?.full_name ?? "??").split(" ").map((n) => n[0]).slice(0, 2).join("")}
          </div>
          <div className="hidden md:block">
            <div className="text-sm font-medium leading-none">{user?.full_name ?? "—"}</div>
            <div className="text-xs text-muted-foreground">{user?.role ?? "viewer"}</div>
          </div>
          <Button variant="ghost" size="icon" aria-label="Sign out" onClick={logout}>
            <LogOut className="h-4 w-4" />
          </Button>
        </div>
      </div>
    </header>
  );
}
