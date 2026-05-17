"use client";

import { useQuery } from "@tanstack/react-query";
import { ArrowRight } from "lucide-react";
import Link from "next/link";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { apiClient } from "@/lib/api";
import { useAppStore } from "@/lib/store";
import type { Journal } from "@/lib/types";
import { cn, formatDate } from "@/lib/utils";

function statusVariant(status: string) {
  if (status === "posted") return "success" as const;
  if (status === "reversed") return "warning" as const;
  return "outline" as const;
}

export default function TransactionsPage() {
  const activeEntityId = useAppStore((s) => s.activeEntityId);

  const { data, isLoading } = useQuery({
    queryKey: ["journals", activeEntityId],
    queryFn: () =>
      apiClient.get<Journal[]>(`/journals?entity_id=${activeEntityId}&limit=200`),
    enabled: !!activeEntityId,
  });

  return (
    <div className="space-y-5">
      <div className="flex items-end justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Journals & transactions</h1>
          <p className="text-muted-foreground text-sm">
            Each row is a balanced journal. Posted journals are immutable — corrections post reversing entries.
          </p>
        </div>
        <Button asChild>
          <Link href="/app/transactions/new">
            New journal <ArrowRight className="h-4 w-4" />
          </Link>
        </Button>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>{data?.length ?? 0} journals</CardTitle>
          <CardDescription>Filtered to the active entity. Switch entities in the top bar.</CardDescription>
        </CardHeader>
        <CardContent className="p-0">
          {isLoading ? (
            <div className="p-6 space-y-3">
              {Array.from({ length: 6 }).map((_, i) => (
                <Skeleton key={i} className="h-9 w-full" />
              ))}
            </div>
          ) : !data || data.length === 0 ? (
            <div className="p-12 text-center text-sm text-muted-foreground">
              No journals yet. Hit <strong>New journal</strong> to record your first entry.
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Journal</TableHead>
                  <TableHead>Date</TableHead>
                  <TableHead>Source</TableHead>
                  <TableHead>Memo</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead className="text-right">Lines</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {data.map((j) => (
                  <TableRow key={j.id} className={cn(j.status === "reversed" && "opacity-60")}>
                    <TableCell className="font-mono text-xs">
                      <Link className="hover:underline" href={`/app/transactions/${j.id}`}>
                        {j.journal_no}
                      </Link>
                    </TableCell>
                    <TableCell>{formatDate(j.posting_date)}</TableCell>
                    <TableCell>
                      <Badge variant="outline" className="capitalize">
                        {j.source}
                      </Badge>
                    </TableCell>
                    <TableCell className="max-w-md truncate text-muted-foreground">
                      {j.memo ?? "—"}
                    </TableCell>
                    <TableCell>
                      <Badge variant={statusVariant(j.status)} className="capitalize">
                        {j.status}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-right tabular text-muted-foreground">
                      {j.lines.length}
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
