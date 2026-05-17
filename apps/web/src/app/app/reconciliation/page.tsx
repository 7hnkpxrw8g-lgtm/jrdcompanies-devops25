"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Check, X } from "lucide-react";
import { useMemo, useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { apiClient } from "@/lib/api";
import { useAppStore } from "@/lib/store";
import type { Account, BankAccount, BankTransaction } from "@/lib/types";
import { formatCurrency, formatDate } from "@/lib/utils";

export default function ReconciliationPage() {
  const activeEntityId = useAppStore((s) => s.activeEntityId);
  const qc = useQueryClient();
  const [selectedAccount, setSelectedAccount] = useState<Record<string, string>>({});

  const { data: txns, isLoading } = useQuery({
    queryKey: ["recon-tx", activeEntityId],
    queryFn: () =>
      apiClient.get<BankTransaction[]>(
        `/banking/transactions?status=unreconciled`
      ),
  });

  const { data: accounts } = useQuery({
    queryKey: ["accounts-recon", activeEntityId],
    queryFn: () =>
      apiClient.get<Account[]>(`/accounts?entity_id=${activeEntityId}`),
    enabled: !!activeEntityId,
  });

  const { data: banks } = useQuery({
    queryKey: ["banks-recon", activeEntityId],
    queryFn: () =>
      apiClient.get<BankAccount[]>(`/banking/accounts?entity_id=${activeEntityId}`),
    enabled: !!activeEntityId,
  });

  const txnsForEntity = useMemo(() => {
    if (!txns || !banks) return [];
    const bankIds = new Set(banks.map((b) => b.id));
    return txns.filter((t) => bankIds.has(t.bank_account_id));
  }, [txns, banks]);

  const categorize = useMutation({
    mutationFn: ({ txnId, accountId }: { txnId: string; accountId: string }) =>
      apiClient.post(`/banking/transactions/${txnId}/categorize`, {
        account_id: accountId,
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["recon-tx"] }),
  });

  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Reconciliation queue</h1>
        <p className="text-sm text-muted-foreground">
          Bank transactions that haven&apos;t been matched to a journal. Pick an account; we&apos;ll
          post the offsetting journal automatically.
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>{txnsForEntity.length} pending</CardTitle>
          <CardDescription>
            Posting a categorization creates a balanced journal: bank account on one side, the
            chosen account on the other.
          </CardDescription>
        </CardHeader>
        <CardContent className="p-0">
          {isLoading ? (
            <div className="p-6 space-y-3">
              {Array.from({ length: 5 }).map((_, i) => (
                <Skeleton key={i} className="h-10 w-full" />
              ))}
            </div>
          ) : txnsForEntity.length === 0 ? (
            <div className="p-12 text-center text-muted-foreground text-sm">
              All caught up. Switch entities or wait for the next sync.
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Date</TableHead>
                  <TableHead>Description</TableHead>
                  <TableHead className="text-right">Amount</TableHead>
                  <TableHead>Categorize as</TableHead>
                  <TableHead className="w-24" />
                </TableRow>
              </TableHeader>
              <TableBody>
                {txnsForEntity.map((t) => (
                  <TableRow key={t.id}>
                    <TableCell className="font-mono text-xs">{formatDate(t.txn_date)}</TableCell>
                    <TableCell>{t.description}</TableCell>
                    <TableCell
                      className={`text-right tabular font-medium ${
                        Number(t.amount) >= 0 ? "text-success" : ""
                      }`}
                    >
                      {formatCurrency(t.amount)}
                    </TableCell>
                    <TableCell>
                      <select
                        className="h-8 rounded-md border bg-background px-2 text-sm w-full max-w-xs"
                        value={selectedAccount[t.id] ?? ""}
                        onChange={(e) =>
                          setSelectedAccount((p) => ({ ...p, [t.id]: e.target.value }))
                        }
                      >
                        <option value="">Choose account</option>
                        {(accounts ?? [])
                          .filter((a) => !a.is_bank)
                          .map((a) => (
                            <option key={a.id} value={a.id}>
                              {a.code} — {a.name}
                            </option>
                          ))}
                      </select>
                    </TableCell>
                    <TableCell>
                      <Button
                        size="sm"
                        variant={selectedAccount[t.id] ? "success" : "outline"}
                        disabled={!selectedAccount[t.id] || categorize.isPending}
                        onClick={() =>
                          categorize.mutate({
                            txnId: t.id,
                            accountId: selectedAccount[t.id],
                          })
                        }
                      >
                        <Check className="h-3.5 w-3.5" />
                        Post
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {categorize.isError ? (
        <div className="rounded-md border border-destructive/40 bg-destructive/5 px-3 py-2 text-sm text-destructive">
          {(categorize.error as Error).message}
        </div>
      ) : null}
    </div>
  );
}
