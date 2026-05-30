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
import { formatCurrency, formatDate } from "@/lib/utils";

interface Bill {
  id: string;
  bill_no: string;
  vendor_id: string;
  issue_date: string;
  due_date: string;
  status: string;
  currency: string;
  total: string;
  amount_paid: string;
  approval_status: string;
}

export default function BillsPage() {
  const activeEntityId = useAppStore((s) => s.activeEntityId);
  const { data, isLoading } = useQuery({
    queryKey: ["bills", activeEntityId],
    queryFn: () => apiClient.get<Bill[]>(`/bills?entity_id=${activeEntityId}`),
    enabled: !!activeEntityId,
  });

  return (
    <div className="space-y-5">
      <div className="flex items-end justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Bills</h1>
          <p className="text-sm text-muted-foreground">
            Vendor bills. Approving posts the AP + expense journal automatically.
          </p>
        </div>
        <Button asChild>
          <Link href="/app/bills/new">New bill</Link>
        </Button>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>{data?.length ?? 0} bills</CardTitle>
          <CardDescription>Filtered to the active entity.</CardDescription>
        </CardHeader>
        <CardContent className="p-0">
          {isLoading ? (
            <div className="p-6 space-y-2">
              {Array.from({ length: 3 }).map((_, i) => (
                <Skeleton key={i} className="h-9 w-full" />
              ))}
            </div>
          ) : !data || data.length === 0 ? (
            <div className="p-12 text-center text-sm text-muted-foreground">
              No bills yet. Create one to populate AP aging.
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Bill #</TableHead>
                  <TableHead>Issued</TableHead>
                  <TableHead>Due</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Approval</TableHead>
                  <TableHead className="text-right">Total</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {data.map((b) => (
                  <TableRow key={b.id}>
                    <TableCell className="font-mono text-xs">{b.bill_no}</TableCell>
                    <TableCell>{formatDate(b.issue_date)}</TableCell>
                    <TableCell>{formatDate(b.due_date)}</TableCell>
                    <TableCell>
                      <Badge variant="outline" className="capitalize">{b.status}</Badge>
                    </TableCell>
                    <TableCell>
                      <Badge
                        variant={b.approval_status === "approved" ? "success" : "warning"}
                        className="capitalize"
                      >
                        {b.approval_status}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-right tabular font-medium">
                      {formatCurrency(b.total, b.currency)}
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
