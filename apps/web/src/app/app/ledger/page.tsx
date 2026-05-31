"use client";

import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { apiClient } from "@/lib/api";
import { useAppStore } from "@/lib/store";
import { cn, formatCurrency, formatDate } from "@/lib/utils";

interface LedgerRow {
  id: string;
  journal_id: string;
  posting_date: string;
  account_code: string;
  account_name: string;
  amount: number;
  debit: number;
  credit: number;
  description: string | null;
}

export default function LedgerPage() {
  const activeEntityId = useAppStore((s) => s.activeEntityId);
  const [filter, setFilter] = useState("");

  const { data, isLoading } = useQuery({
    queryKey: ["ledger", activeEntityId],
    queryFn: () =>
      apiClient.get<LedgerRow[]>(`/reports/general-ledger?entity_id=${activeEntityId}`),
    enabled: !!activeEntityId,
  });

  const rows = (data ?? []).filter((row) => {
    if (!filter) return true;
    const haystack = `${row.account_code} ${row.account_name} ${row.description ?? ""}`.toLowerCase();
    return haystack.includes(filter.toLowerCase());
  });

  return (
    <div className="space-y-5">
      <div className="flex items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">General ledger</h1>
          <p className="text-muted-foreground text-sm">
            Append-only record of every posted journal line. This list mirrors the underlying
            <code className="text-foreground ml-1 px-1.5 py-0.5 rounded bg-muted text-xs">ledger_entry</code>
            table — no edits, no deletes, ever.
          </p>
        </div>
        <Input
          placeholder="Filter by account or memo…"
          className="max-w-xs"
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
        />
      </div>

      <Card>
        <CardHeader>
          <CardTitle>{rows.length} entries</CardTitle>
          <CardDescription>
            Newest first. Debits are positive, credits negative — and per journal they sum to zero.
          </CardDescription>
        </CardHeader>
        <CardContent className="p-0">
          {isLoading ? (
            <div className="p-6 space-y-3">
              {Array.from({ length: 6 }).map((_, i) => (
                <Skeleton key={i} className="h-9 w-full" />
              ))}
            </div>
          ) : rows.length === 0 ? (
            <div className="p-12 text-center text-sm text-muted-foreground">
              No ledger entries yet. Post a journal to populate this table.
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Date</TableHead>
                  <TableHead>Account</TableHead>
                  <TableHead>Description</TableHead>
                  <TableHead className="text-right">Debit</TableHead>
                  <TableHead className="text-right">Credit</TableHead>
                  <TableHead className="text-right">Journal</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {rows
                  .slice()
                  .reverse()
                  .map((row) => (
                    <TableRow key={row.id}>
                      <TableCell className="font-mono text-xs whitespace-nowrap">
                        {formatDate(row.posting_date)}
                      </TableCell>
                      <TableCell>
                        <div className="flex items-center gap-2">
                          <Badge variant="outline" className="font-mono text-xs">
                            {row.account_code}
                          </Badge>
                          <span className="font-medium">{row.account_name}</span>
                        </div>
                      </TableCell>
                      <TableCell className="text-muted-foreground max-w-[20rem] truncate">
                        {row.description ?? "—"}
                      </TableCell>
                      <TableCell
                        className={cn(
                          "text-right tabular font-medium",
                          row.debit > 0 ? "" : "text-muted-foreground"
                        )}
                      >
                        {row.debit > 0 ? formatCurrency(row.debit) : "—"}
                      </TableCell>
                      <TableCell
                        className={cn(
                          "text-right tabular font-medium",
                          row.credit > 0 ? "" : "text-muted-foreground"
                        )}
                      >
                        {row.credit > 0 ? formatCurrency(row.credit) : "—"}
                      </TableCell>
                      <TableCell className="text-right font-mono text-xs text-muted-foreground">
                        {row.journal_id.slice(0, 8)}
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
