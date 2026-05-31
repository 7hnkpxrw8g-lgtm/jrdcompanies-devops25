"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ChevronLeft, RotateCcw } from "lucide-react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { apiClient } from "@/lib/api";
import type { Journal } from "@/lib/types";
import { formatCurrency, formatDate } from "@/lib/utils";

export default function JournalDetailPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const qc = useQueryClient();
  const id = params.id;

  const { data, isLoading } = useQuery({
    queryKey: ["journal", id],
    queryFn: () => apiClient.get<Journal>(`/journals/${id}`),
  });

  const post = useMutation({
    mutationFn: () => apiClient.post<Journal>(`/journals/${id}/post`, {}),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["journal", id] }),
  });

  const reverse = useMutation({
    mutationFn: () => apiClient.post<Journal>(`/journals/${id}/reverse`, {}),
    onSuccess: (rev) => {
      qc.invalidateQueries({ queryKey: ["journal", id] });
      router.push(`/app/transactions/${rev.id}`);
    },
  });

  return (
    <div className="space-y-5 max-w-5xl">
      <div className="flex items-center gap-2 text-sm text-muted-foreground">
        <Link href="/app/transactions" className="hover:text-foreground inline-flex items-center gap-1">
          <ChevronLeft className="h-3.5 w-3.5" /> All journals
        </Link>
      </div>

      {isLoading || !data ? (
        <Skeleton className="h-64 w-full" />
      ) : (
        <>
          <div className="flex items-end justify-between">
            <div>
              <h1 className="text-2xl font-semibold tracking-tight font-mono">{data.journal_no}</h1>
              <p className="text-sm text-muted-foreground">{data.memo ?? "No memo"}</p>
            </div>
            <div className="flex items-center gap-2">
              {data.status === "draft" ? (
                <Button disabled={post.isPending} onClick={() => post.mutate()}>
                  Post journal
                </Button>
              ) : null}
              {data.status === "posted" ? (
                <Button variant="outline" disabled={reverse.isPending} onClick={() => reverse.mutate()}>
                  <RotateCcw className="h-4 w-4" /> Reverse
                </Button>
              ) : null}
            </div>
          </div>

          <Card>
            <CardHeader>
              <div className="flex flex-wrap items-center gap-4">
                <div>
                  <div className="text-xs uppercase text-muted-foreground tracking-wide">Posting date</div>
                  <div className="font-medium">{formatDate(data.posting_date)}</div>
                </div>
                <div>
                  <div className="text-xs uppercase text-muted-foreground tracking-wide">Source</div>
                  <Badge variant="outline" className="capitalize mt-1">{data.source}</Badge>
                </div>
                <div>
                  <div className="text-xs uppercase text-muted-foreground tracking-wide">Status</div>
                  <Badge
                    variant={data.status === "posted" ? "success" : data.status === "reversed" ? "warning" : "outline"}
                    className="capitalize mt-1"
                  >
                    {data.status}
                  </Badge>
                </div>
                <div>
                  <div className="text-xs uppercase text-muted-foreground tracking-wide">Currency</div>
                  <div className="font-medium">{data.currency} · FX {data.fx_rate}</div>
                </div>
                {data.posted_at ? (
                  <div>
                    <div className="text-xs uppercase text-muted-foreground tracking-wide">Posted</div>
                    <div className="font-medium">{formatDate(data.posted_at)}</div>
                  </div>
                ) : null}
              </div>
            </CardHeader>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Lines</CardTitle>
              <CardDescription>Frozen after posting. Reversals create a new offsetting journal.</CardDescription>
            </CardHeader>
            <CardContent className="p-0">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>#</TableHead>
                    <TableHead>Account</TableHead>
                    <TableHead>Description</TableHead>
                    <TableHead className="text-right">Debit</TableHead>
                    <TableHead className="text-right">Credit</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {data.lines.map((line) => (
                    <TableRow key={line.id ?? line.line_no}>
                      <TableCell className="text-muted-foreground tabular">{line.line_no}</TableCell>
                      <TableCell className="font-mono text-xs">{line.account_id.slice(0, 8)}</TableCell>
                      <TableCell className="text-muted-foreground">{line.description ?? "—"}</TableCell>
                      <TableCell className="text-right tabular font-medium">
                        {Number(line.debit) > 0 ? formatCurrency(line.debit) : "—"}
                      </TableCell>
                      <TableCell className="text-right tabular font-medium">
                        {Number(line.credit) > 0 ? formatCurrency(line.credit) : "—"}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        </>
      )}
    </div>
  );
}
