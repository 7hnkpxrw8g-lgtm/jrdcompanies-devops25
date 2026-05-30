"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { CsvImportButton } from "@/components/app/csv-import";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { apiClient } from "@/lib/api";
import { useAppStore } from "@/lib/store";
import type { BankAccount, BankTransaction } from "@/lib/types";
import { formatCurrency, formatDate, relativeDate } from "@/lib/utils";

export default function BankingPage() {
  const activeEntityId = useAppStore((s) => s.activeEntityId);

  const { data: accounts, isLoading: aLoading } = useQuery({
    queryKey: ["bank-accounts", activeEntityId],
    queryFn: () =>
      apiClient.get<BankAccount[]>(`/banking/accounts?entity_id=${activeEntityId}`),
    enabled: !!activeEntityId,
  });

  const { data: txns, isLoading: tLoading } = useQuery({
    queryKey: ["bank-tx", activeEntityId],
    queryFn: () => apiClient.get<BankTransaction[]>(`/banking/transactions`),
  });

  return (
    <div className="space-y-5">
      <div className="flex items-end justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Banking</h1>
          <p className="text-sm text-muted-foreground">
            Connected accounts, latest sync, and the live transaction feed.
          </p>
        </div>
        <Button asChild>
          <Link href="/app/integrations">Connect bank</Link>
        </Button>
      </div>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {aLoading
          ? Array.from({ length: 3 }).map((_, i) => <Skeleton key={i} className="h-32" />)
          : (accounts ?? []).map((acct) => (
              <Card key={acct.id}>
                <CardHeader>
                  <div className="flex items-center justify-between">
                    <div>
                      <CardTitle className="text-base">{acct.name}</CardTitle>
                      <CardDescription>
                        {acct.institution ?? "—"} · ****{acct.mask ?? ""}
                      </CardDescription>
                    </div>
                    <Badge variant="outline" className="capitalize">{acct.account_type}</Badge>
                  </div>
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-semibold tabular">
                    {formatCurrency(acct.last_balance, acct.currency)}
                  </div>
                  <div className="mt-1 flex items-center justify-between text-xs text-muted-foreground">
                    <span>Synced {acct.last_sync_at ? relativeDate(acct.last_sync_at) : "—"}</span>
                    <CsvImportButton bankAccountId={acct.id} />
                  </div>
                </CardContent>
              </Card>
            ))}
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Recent feed</CardTitle>
          <CardDescription>
            All bank transactions across connected accounts. Unreconciled rows show up on the
            <Link href="/app/reconciliation" className="text-primary ml-1 hover:underline">
              reconciliation queue
            </Link>.
          </CardDescription>
        </CardHeader>
        <CardContent className="p-0">
          {tLoading ? (
            <div className="p-6 space-y-2">
              {Array.from({ length: 6 }).map((_, i) => (
                <Skeleton key={i} className="h-8 w-full" />
              ))}
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Date</TableHead>
                  <TableHead>Description</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead className="text-right">Amount</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {(txns ?? []).slice(0, 50).map((t) => (
                  <TableRow key={t.id}>
                    <TableCell className="whitespace-nowrap text-xs font-mono">
                      {formatDate(t.txn_date)}
                    </TableCell>
                    <TableCell>{t.description}</TableCell>
                    <TableCell>
                      <Badge
                        variant={
                          t.status === "posted"
                            ? "success"
                            : t.status === "unreconciled"
                            ? "warning"
                            : "outline"
                        }
                        className="capitalize"
                      >
                        {t.status}
                      </Badge>
                    </TableCell>
                    <TableCell
                      className={`text-right tabular font-medium ${
                        Number(t.amount) >= 0 ? "text-success" : "text-foreground"
                      }`}
                    >
                      {formatCurrency(t.amount)}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
