"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@/lib/api";
import { useAppStore } from "@/lib/store";
import type { User } from "@/lib/types";

export function AuthGuard({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const setUser = useAppStore((s) => s.setUser);
  const [ready, setReady] = useState(false);

  const { data, error, isLoading } = useQuery({
    queryKey: ["me"],
    queryFn: () => apiClient.get<User>("/auth/me"),
    retry: false,
  });

  useEffect(() => {
    if (isLoading) return;
    if (error) {
      router.replace("/login");
      return;
    }
    if (data) {
      setUser(data);
      setReady(true);
    }
  }, [data, error, isLoading, router, setUser]);

  if (!ready) {
    return (
      <div className="grid min-h-screen place-items-center">
        <div className="h-8 w-8 rounded-full border-2 border-primary border-r-transparent animate-spin" />
      </div>
    );
  }
  return <>{children}</>;
}
