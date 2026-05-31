"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { apiClient } from "@/lib/api";
import { useAppStore } from "@/lib/store";
import type { Invoice } from "@/lib/types";
import { formatCurrency, formatDate } from "@/lib/utils";

export default function InvoicesPage() {
  const activeEntityId = useAppStore((s) => s.activeEntityId);
  const { data, isLoading } = useQuery({
    queryKey: ["invoices", activeEntityId],
    queryFn: () =>
      apiClient.get<Invoice[]>(`/invoices?entity_id=${activeEntityId}`),
    enabled: !!activeEntityId,
  });

  return (
    <div className="space-y-5">
      <div className="flex items-end justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Invoices</h1>
          <p className="text-sm text-muted-foreground">
            Approved invoices post AR + revenue journals automatically.
          </p>
        </div>
        <Button asChild>
          <Link href="/app/invoices/new">New invoice</Link>
        </Button>
      </div>
      <Card>
        <CardHeader>
          <CardTitle>{data?.length ?? 0} invoices</CardTitle>
          <CardDescription>Filtered to the active entity.</CardDescription>
        </CardHeader>
        <CardContent className="p-0">
          {isLoading ? (
            <div className="p-6 space-y-2">
              {Array.from({ length: 3 }).map((_, i) => (
                <Skeleton key={i} className="h-8 w-full" />
              ))}
            </div>
          ) : !data || data.length === 0 ? (
            <div className="p-12 text-center text-sm text-muted-foreground">
              No invoices yet.
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Invoice #</TableHead>
                  <TableHead>Issued</TableHead>
                  <TableHead>Due</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead className="text-right">Total</TableHead>
                  <TableHead className="text-right">Paid</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {data.map((inv) => (
                  <TableRow key={inv.id}>
                    <TableCell className="font-mono text-xs">{inv.invoice_no}</TableCell>
                    <TableCell>{formatDate(inv.issue_date)}</TableCell>
                    <TableCell>{formatDate(inv.due_date)}</TableCell>
                    <TableCell>
                      <Badge variant="outline" className="capitalize">{inv.status}</Badge>
                    </TableCell>
                    <TableCell className="text-right tabular font-medium">
                      {formatCurrency(inv.total, inv.currency)}
                    </TableCell>
                    <TableCell className="text-right tabular text-muted-foreground">
                      {formatCurrency(inv.amount_paid, inv.currency)}
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
