"use client";

import { useQuery } from "@tanstack/react-query";
import { ArrowDown, ArrowUp, ClipboardCheck, CreditCard, DollarSign, TrendingUp, Wallet } from "lucide-react";
import Link from "next/link";
import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { apiClient } from "@/lib/api";
import { useAppStore } from "@/lib/store";
import type { DashboardSummary } from "@/lib/types";
import { cn, formatCurrency } from "@/lib/utils";

export default function DashboardPage() {
  const activeEntityId = useAppStore((s) => s.activeEntityId);

  const { data, isLoading } = useQuery({
    queryKey: ["dashboard", activeEntityId],
    queryFn: () =>
      apiClient.get<DashboardSummary>(`/dashboard/summary?entity_id=${activeEntityId}`),
    enabled: !!activeEntityId,
  });

  return (
    <div className="space-y-6">
      <div className="flex items-end justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Dashboard</h1>
          <p className="text-muted-foreground text-sm">
            Live state of your books — refreshed every 30 seconds.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button asChild variant="outline" size="sm">
            <Link href="/app/transactions">New transaction</Link>
          </Button>
          <Button asChild size="sm">
            <Link href="/app/invoices/new">New invoice</Link>
          </Button>
        </div>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <Kpi
          title="Cash on hand"
          icon={<Wallet className="h-4 w-4" />}
          value={formatCurrency(data?.cash_balance ?? 0)}
          hint={`${data?.bank_accounts.length ?? 0} bank accounts`}
          loading={isLoading}
        />
        <Kpi
          title="MTD net income"
          icon={<TrendingUp className="h-4 w-4" />}
          value={formatCurrency(data?.month_to_date.net_income ?? 0)}
          hint={
            data
              ? `${formatCurrency(data.month_to_date.revenue)} rev · ${formatCurrency(
                  data.month_to_date.expense
                )} exp`
              : ""
          }
          loading={isLoading}
          tone={
            (data?.month_to_date.net_income ?? 0) >= 0 ? "positive" : "negative"
          }
        />
        <Kpi
          title="AR outstanding"
          icon={<DollarSign className="h-4 w-4" />}
          value={formatCurrency(data?.ar_outstanding ?? 0)}
          hint="Click to view AR aging"
          href="/app/reports?r=ar-aging"
          loading={isLoading}
        />
        <Kpi
          title="Unreconciled"
          icon={<ClipboardCheck className="h-4 w-4" />}
          value={`${data?.unreconciled_count ?? 0}`}
          hint="Open the reconciliation queue"
          href="/app/reconciliation"
          loading={isLoading}
          tone={(data?.unreconciled_count ?? 0) > 0 ? "warning" : undefined}
        />
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <CardHeader>
            <div className="flex items-center justify-between">
              <div>
                <CardTitle>Revenue vs expenses</CardTitle>
                <CardDescription>Trailing six months — both entities consolidated for this entity.</CardDescription>
              </div>
              <Badge variant="outline">USD</Badge>
            </div>
          </CardHeader>
          <CardContent className="h-72">
            {isLoading ? (
              <Skeleton className="h-full w-full" />
            ) : data && data.revenue_trend.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={data.revenue_trend} margin={{ top: 5, right: 10, left: 0, bottom: 0 }}>
                  <defs>
                    <linearGradient id="rev" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="hsl(var(--primary))" stopOpacity={0.4} />
                      <stop offset="100%" stopColor="hsl(var(--primary))" stopOpacity={0} />
                    </linearGradient>
                    <linearGradient id="exp" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="hsl(var(--destructive))" stopOpacity={0.3} />
                      <stop offset="100%" stopColor="hsl(var(--destructive))" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                  <XAxis dataKey="month" tick={{ fontSize: 12, fill: "hsl(var(--muted-foreground))" }} />
                  <YAxis
                    tick={{ fontSize: 12, fill: "hsl(var(--muted-foreground))" }}
                    tickFormatter={(v: number) => `$${Math.round(v / 1000)}k`}
                  />
                  <Tooltip
                    contentStyle={{
                      background: "hsl(var(--background))",
                      border: "1px solid hsl(var(--border))",
                      borderRadius: 8,
                      fontSize: 12,
                    }}
                    formatter={(v: number) => formatCurrency(v)}
                  />
                  <Area type="monotone" dataKey="revenue" stroke="hsl(var(--primary))" fill="url(#rev)" strokeWidth={2} />
                  <Area type="monotone" dataKey="expense" stroke="hsl(var(--destructive))" fill="url(#exp)" strokeWidth={2} />
                </AreaChart>
              </ResponsiveContainer>
            ) : null}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Bank accounts</CardTitle>
            <CardDescription>Last balances pulled from feeds.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            {isLoading
              ? Array.from({ length: 3 }).map((_, i) => <Skeleton key={i} className="h-12 w-full" />)
              : (data?.bank_accounts ?? []).map((acct) => (
                  <div
                    key={acct.id}
                    className="flex items-center justify-between rounded-md border bg-card px-3 py-2.5"
                  >
                    <div>
                      <div className="text-sm font-medium">{acct.name}</div>
                      <div className="text-xs text-muted-foreground">{acct.currency}</div>
                    </div>
                    <div className="font-medium tabular">{formatCurrency(acct.balance, acct.currency)}</div>
                  </div>
                ))}
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>A/R outstanding</CardTitle>
            <CardDescription>Customers who owe you money.</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-semibold tabular">
              {formatCurrency(data?.ar_outstanding ?? 0)}
            </div>
            <p className="mt-2 text-sm text-muted-foreground">
              Drill into <Link href="/app/reports?r=ar-aging" className="underline">AR aging</Link> for the
              full breakdown by bucket.
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>A/P outstanding</CardTitle>
            <CardDescription>Vendors waiting on payment.</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-semibold tabular">
              {formatCurrency(data?.ap_outstanding ?? 0)}
            </div>
            <p className="mt-2 text-sm text-muted-foreground">
              Review <Link href="/app/bills" className="underline">bills awaiting approval</Link> before the
              next pay run.
            </p>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

interface KpiProps {
  title: string;
  icon: React.ReactNode;
  value: string;
  hint?: string;
  href?: string;
  loading?: boolean;
  tone?: "positive" | "negative" | "warning";
}

function Kpi({ title, icon, value, hint, href, loading, tone }: KpiProps) {
  const inner = (
    <Card className={cn("h-full", href && "transition-all hover:border-primary/40 hover:shadow")}>
      <CardContent className="p-5">
        <div className="flex items-center justify-between text-muted-foreground">
          <span className="text-xs font-medium uppercase tracking-wide">{title}</span>
          <span
            className={cn(
              "grid h-7 w-7 place-items-center rounded-md bg-muted",
              tone === "positive" && "bg-success/10 text-success",
              tone === "negative" && "bg-destructive/10 text-destructive",
              tone === "warning" && "bg-warning/15 text-warning"
            )}
          >
            {icon}
          </span>
        </div>
        <div className="mt-3 text-2xl font-semibold tabular">
          {loading ? <Skeleton className="h-7 w-32" /> : value}
        </div>
        {hint ? (
          <div className="mt-2 flex items-center gap-1.5 text-xs text-muted-foreground">
            {tone === "positive" ? (
              <ArrowUp className="h-3 w-3 text-success" />
            ) : tone === "negative" ? (
              <ArrowDown className="h-3 w-3 text-destructive" />
            ) : null}
            {hint}
          </div>
        ) : null}
      </CardContent>
    </Card>
  );
  return href ? <Link href={href}>{inner}</Link> : inner;
}
