"use client";

import { useQuery } from "@tanstack/react-query";
import { useSearchParams } from "next/navigation";
import { Suspense, useMemo, useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { apiClient } from "@/lib/api";
import { useAppStore } from "@/lib/store";
import type {
  BalanceSheetResponse,
  PnLResponse,
  TrialBalanceRow,
} from "@/lib/types";
import { cn, formatCurrency, formatDate } from "@/lib/utils";

const REPORTS = [
  { key: "pnl", label: "Profit & Loss" },
  { key: "balance-sheet", label: "Balance sheet" },
  { key: "trial-balance", label: "Trial balance" },
  { key: "ar-aging", label: "A/R aging" },
] as const;
type ReportKey = (typeof REPORTS)[number]["key"];

export default function ReportsPage() {
  return (
    <Suspense fallback={null}>
      <ReportsView />
    </Suspense>
  );
}

function ReportsView() {
  const params = useSearchParams();
  const initial = (params.get("r") as ReportKey) || "pnl";
  const [report, setReport] = useState<ReportKey>(initial);
  const activeEntityId = useAppStore((s) => s.activeEntityId);
  const today = new Date().toISOString().slice(0, 10);
  const monthStart = new Date();
  monthStart.setDate(1);
  const [start, setStart] = useState(monthStart.toISOString().slice(0, 10));
  const [end, setEnd] = useState(today);

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Reports</h1>
          <p className="text-sm text-muted-foreground">
            All reports run live against the immutable ledger. Drill any number to the source journals.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <input
            type="date"
            value={start}
            onChange={(e) => setStart(e.target.value)}
            className="h-9 rounded-md border bg-background px-3 text-sm"
          />
          <span className="text-muted-foreground text-sm">→</span>
          <input
            type="date"
            value={end}
            onChange={(e) => setEnd(e.target.value)}
            className="h-9 rounded-md border bg-background px-3 text-sm"
          />
        </div>
      </div>

      <div className="flex flex-wrap gap-2 border-b">
        {REPORTS.map((r) => (
          <button
            key={r.key}
            onClick={() => setReport(r.key)}
            className={cn(
              "px-3 py-2 text-sm font-medium border-b-2 -mb-px transition-colors",
              report === r.key
                ? "border-primary text-foreground"
                : "border-transparent text-muted-foreground hover:text-foreground"
            )}
          >
            {r.label}
          </button>
        ))}
      </div>

      {report === "pnl" && (
        <PnLReport entityId={activeEntityId} start={start} end={end} />
      )}
      {report === "balance-sheet" && <BalanceSheet entityId={activeEntityId} asOf={end} />}
      {report === "trial-balance" && <TrialBalance entityId={activeEntityId} asOf={end} />}
      {report === "ar-aging" && <ARAgingReport entityId={activeEntityId} asOf={end} />}
    </div>
  );
}

function PnLReport({ entityId, start, end }: { entityId: string | null; start: string; end: string }) {
  const { data, isLoading } = useQuery({
    queryKey: ["pnl", entityId, start, end],
    queryFn: () =>
      apiClient.get<PnLResponse>(`/reports/pnl?entity_id=${entityId}&start=${start}&end=${end}`),
    enabled: !!entityId,
  });

  if (isLoading || !data) return <Skeleton className="h-96 w-full" />;
  return (
    <Card>
      <CardHeader>
        <CardTitle>Profit & Loss</CardTitle>
        <CardDescription>
          {formatDate(data.start)} → {formatDate(data.end)}
        </CardDescription>
      </CardHeader>
      <CardContent className="p-0">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="w-24">Code</TableHead>
              <TableHead>Account</TableHead>
              <TableHead className="text-right">Amount</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            <TableRow className="bg-accent/30 font-semibold uppercase text-xs">
              <TableCell colSpan={3}>Revenue</TableCell>
            </TableRow>
            {data.revenue.map((r) => (
              <TableRow key={r.account_id}>
                <TableCell className="font-mono text-xs">{r.code}</TableCell>
                <TableCell>{r.name}</TableCell>
                <TableCell className="text-right tabular">{formatCurrency(r.amount)}</TableCell>
              </TableRow>
            ))}
            <TableRow className="font-medium">
              <TableCell colSpan={2} className="text-right">
                Total revenue
              </TableCell>
              <TableCell className="text-right tabular">{formatCurrency(data.revenue_total)}</TableCell>
            </TableRow>

            <TableRow className="bg-accent/30 font-semibold uppercase text-xs">
              <TableCell colSpan={3}>Expenses</TableCell>
            </TableRow>
            {data.expense.map((r) => (
              <TableRow key={r.account_id}>
                <TableCell className="font-mono text-xs">{r.code}</TableCell>
                <TableCell>{r.name}</TableCell>
                <TableCell className="text-right tabular">{formatCurrency(r.amount)}</TableCell>
              </TableRow>
            ))}
            <TableRow className="font-medium">
              <TableCell colSpan={2} className="text-right">
                Total expenses
              </TableCell>
              <TableCell className="text-right tabular">{formatCurrency(data.expense_total)}</TableCell>
            </TableRow>

            <TableRow className="border-t-2 font-semibold">
              <TableCell colSpan={2} className="text-right uppercase tracking-wide">
                Net income
              </TableCell>
              <TableCell
                className={cn(
                  "text-right tabular",
                  Number(data.net_income) >= 0 ? "text-success" : "text-destructive"
                )}
              >
                {formatCurrency(data.net_income)}
              </TableCell>
            </TableRow>
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  );
}

function BalanceSheet({ entityId, asOf }: { entityId: string | null; asOf: string }) {
  const { data, isLoading } = useQuery({
    queryKey: ["bs", entityId, asOf],
    queryFn: () =>
      apiClient.get<BalanceSheetResponse>(
        `/reports/balance-sheet?entity_id=${entityId}&as_of=${asOf}`
      ),
    enabled: !!entityId,
  });

  const balance = useMemo(() => {
    if (!data) return { delta: 0, ok: true };
    const delta =
      Number(data.assets_total) - (Number(data.liabilities_total) + Number(data.equity_total));
    return { delta, ok: Math.abs(delta) < 0.01 };
  }, [data]);

  if (isLoading || !data) return <Skeleton className="h-96 w-full" />;

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle>Balance sheet</CardTitle>
            <CardDescription>As of {formatDate(data.as_of)}</CardDescription>
          </div>
          <Badge variant={balance.ok ? "success" : "destructive"}>
            {balance.ok ? "Balanced" : `Off by ${formatCurrency(balance.delta)}`}
          </Badge>
        </div>
      </CardHeader>
      <CardContent className="grid gap-6 lg:grid-cols-3">
        <Section title="Assets" rows={data.assets} total={data.assets_total} />
        <Section title="Liabilities" rows={data.liabilities} total={data.liabilities_total} />
        <Section title="Equity" rows={data.equity} total={data.equity_total} extraRow={{
          label: "Retained earnings", amount: data.retained_earnings,
        }} />
      </CardContent>
    </Card>
  );
}

function Section({
  title,
  rows,
  total,
  extraRow,
}: {
  title: string;
  rows: { code: string; name: string; balance: string }[];
  total: string;
  extraRow?: { label: string; amount: string };
}) {
  return (
    <div>
      <h3 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground mb-2">
        {title}
      </h3>
      <ul className="space-y-1 text-sm">
        {rows.map((row) => (
          <li key={row.code} className="flex items-center justify-between border-b py-1.5">
            <span>
              <span className="font-mono text-xs text-muted-foreground mr-2">{row.code}</span>
              {row.name}
            </span>
            <span className="tabular font-medium">{formatCurrency(row.balance)}</span>
          </li>
        ))}
        {extraRow && Number(extraRow.amount) !== 0 ? (
          <li className="flex items-center justify-between border-b py-1.5 italic text-muted-foreground">
            <span>{extraRow.label}</span>
            <span className="tabular">{formatCurrency(extraRow.amount)}</span>
          </li>
        ) : null}
        <li className="flex items-center justify-between pt-2 font-semibold">
          <span>Total {title.toLowerCase()}</span>
          <span className="tabular">{formatCurrency(total)}</span>
        </li>
      </ul>
    </div>
  );
}

function TrialBalance({ entityId, asOf }: { entityId: string | null; asOf: string }) {
  const { data, isLoading } = useQuery({
    queryKey: ["tb", entityId, asOf],
    queryFn: () =>
      apiClient.get<TrialBalanceRow[]>(
        `/reports/trial-balance?entity_id=${entityId}&as_of=${asOf}`
      ),
    enabled: !!entityId,
  });

  if (isLoading) return <Skeleton className="h-96 w-full" />;
  const rows = data ?? [];
  const totalD = rows.reduce((s, r) => s + Number(r.debit), 0);
  const totalC = rows.reduce((s, r) => s + Number(r.credit), 0);

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle>Trial balance</CardTitle>
            <CardDescription>As of {formatDate(asOf)} — sums of every account.</CardDescription>
          </div>
          <Badge variant={Math.abs(totalD - totalC) < 0.01 ? "success" : "destructive"}>
            {Math.abs(totalD - totalC) < 0.01 ? "In balance" : "OUT OF BALANCE"}
          </Badge>
        </div>
      </CardHeader>
      <CardContent className="p-0">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="w-24">Code</TableHead>
              <TableHead>Account</TableHead>
              <TableHead>Type</TableHead>
              <TableHead className="text-right">Debit</TableHead>
              <TableHead className="text-right">Credit</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {rows.map((r) => (
              <TableRow key={r.account_id}>
                <TableCell className="font-mono text-xs">{r.code}</TableCell>
                <TableCell>{r.name}</TableCell>
                <TableCell>
                  <Badge variant="outline" className="capitalize">{r.type}</Badge>
                </TableCell>
                <TableCell className="text-right tabular font-medium">
                  {Number(r.debit) > 0 ? formatCurrency(r.debit) : "—"}
                </TableCell>
                <TableCell className="text-right tabular font-medium">
                  {Number(r.credit) > 0 ? formatCurrency(r.credit) : "—"}
                </TableCell>
              </TableRow>
            ))}
            <TableRow className="font-semibold border-t-2">
              <TableCell colSpan={3} className="text-right uppercase tracking-wide">Totals</TableCell>
              <TableCell className="text-right tabular">{formatCurrency(totalD)}</TableCell>
              <TableCell className="text-right tabular">{formatCurrency(totalC)}</TableCell>
            </TableRow>
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  );
}

function ARAgingReport({ entityId, asOf }: { entityId: string | null; asOf: string }) {
  const { data, isLoading } = useQuery({
    queryKey: ["ar-aging", entityId, asOf],
    queryFn: () =>
      apiClient.get<
        {
          customer_id: string;
          customer: string;
          current: number;
          "1_30": number;
          "31_60": number;
          "61_90": number;
          over_90: number;
          total: number;
        }[]
      >(`/reports/ar-aging?entity_id=${entityId}&as_of=${asOf}`),
    enabled: !!entityId,
  });

  if (isLoading) return <Skeleton className="h-72 w-full" />;
  const rows = data ?? [];
  if (rows.length === 0) {
    return (
      <Card>
        <CardContent className="p-12 text-center text-sm text-muted-foreground">
          No outstanding A/R. Create some invoices to populate this report.
        </CardContent>
      </Card>
    );
  }
  return (
    <Card>
      <CardHeader>
        <CardTitle>A/R aging</CardTitle>
        <CardDescription>By customer · As of {formatDate(asOf)}</CardDescription>
      </CardHeader>
      <CardContent className="p-0">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Customer</TableHead>
              <TableHead className="text-right">Current</TableHead>
              <TableHead className="text-right">1-30</TableHead>
              <TableHead className="text-right">31-60</TableHead>
              <TableHead className="text-right">61-90</TableHead>
              <TableHead className="text-right">90+</TableHead>
              <TableHead className="text-right">Total</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {rows.map((r) => (
              <TableRow key={r.customer_id}>
                <TableCell>{r.customer}</TableCell>
                <TableCell className="text-right tabular">{formatCurrency(r.current)}</TableCell>
                <TableCell className="text-right tabular">{formatCurrency(r["1_30"])}</TableCell>
                <TableCell className="text-right tabular">{formatCurrency(r["31_60"])}</TableCell>
                <TableCell className="text-right tabular">{formatCurrency(r["61_90"])}</TableCell>
                <TableCell className="text-right tabular">{formatCurrency(r.over_90)}</TableCell>
                <TableCell className="text-right tabular font-semibold">{formatCurrency(r.total)}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  );
}
