"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { apiClient, setToken } from "@/lib/api";
import { useAppStore } from "@/lib/store";

interface LoginResponse {
  access_token: string;
  user_id: string;
  org_id: string | null;
  org_slug: string | null;
}

export default function LoginPage() {
  const router = useRouter();
  const setUser = useAppStore((s) => s.setUser);
  const [email, setEmail] = useState("demo@jrdbooks.io");
  const [password, setPassword] = useState("demo");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const data = await apiClient.post<LoginResponse>("/auth/token", { email, password });
      setToken(data.access_token);
      const me = await apiClient.get<{
        id: string;
        email: string;
        full_name: string;
        org_id: string | null;
        org_slug: string | null;
        role: string | null;
      }>("/auth/me");
      setUser(me);
      router.push("/app");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Login failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen grid place-items-center bg-gradient-to-br from-background via-accent/40 to-background p-6">
      <Card className="w-full max-w-md shadow-lg">
        <CardHeader>
          <div className="h-10 w-10 rounded-lg bg-primary text-primary-foreground grid place-items-center font-bold mb-3">
            JR
          </div>
          <CardTitle className="text-2xl">Sign in to JRDbooks</CardTitle>
          <CardDescription>Use the seeded demo credentials to explore the platform.</CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={submit} className="space-y-3">
            <div className="space-y-1.5">
              <label htmlFor="email" className="text-sm font-medium">Email</label>
              <Input
                id="email"
                type="email"
                value={email}
                autoComplete="email"
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@company.com"
                required
              />
            </div>
            <div className="space-y-1.5">
              <label htmlFor="password" className="text-sm font-medium">Password</label>
              <Input
                id="password"
                type="password"
                value={password}
                autoComplete="current-password"
                onChange={(e) => setPassword(e.target.value)}
                required
              />
            </div>
            {error ? (
              <div className="rounded-md border border-destructive/30 bg-destructive/5 px-3 py-2 text-sm text-destructive">
                {error}
              </div>
            ) : null}
            <Button type="submit" className="w-full" disabled={loading}>
              {loading ? "Signing in…" : "Sign in"}
            </Button>
            <p className="text-xs text-muted-foreground text-center mt-2">
              Demo seed: <code className="text-foreground">demo@jrdbooks.io</code> / <code className="text-foreground">demo</code>
            </p>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
