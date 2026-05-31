"use client";

import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { apiClient } from "@/lib/api";
import { formatDate } from "@/lib/utils";

interface AuditEvent {
  id: string;
  occurred_at: string;
  actor_user_id: string | null;
  actor_label: string | null;
  source: string;
  action: string;
  target_kind: string;
  target_id: string | null;
  request_id: string | null;
  before: Record<string, unknown>;
  after: Record<string, unknown>;
}

export default function AuditPage() {
  const [filter, setFilter] = useState("");
  const { data, isLoading } = useQuery({
    queryKey: ["audit-events"],
    queryFn: () => apiClient.get<AuditEvent[]>("/audit/events?limit=500"),
  });

  const rows = (data ?? []).filter((row) => {
    if (!filter) return true;
    const haystack =
      `${row.action} ${row.target_kind} ${row.source} ${row.actor_label ?? ""} ` +
      JSON.stringify(row.after).slice(0, 200);
    return haystack.toLowerCase().includes(filter.toLowerCase());
  });

  return (
    <div className="space-y-5">
      <div className="flex items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Audit logs</h1>
          <p className="text-sm text-muted-foreground">
            Append-only event stream. Every write the API performs lands here with
            actor, source, request ID, and before/after diff.
          </p>
        </div>
        <Input
          placeholder="Filter by action, target, actor…"
          className="max-w-sm"
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
        />
      </div>

      <Card>
        <CardHeader>
          <CardTitle>{rows.length} events</CardTitle>
          <CardDescription>Most recent first.</CardDescription>
        </CardHeader>
        <CardContent className="p-0">
          {isLoading ? (
            <div className="p-6 space-y-2">
              {Array.from({ length: 6 }).map((_, i) => (
                <Skeleton key={i} className="h-9 w-full" />
              ))}
            </div>
          ) : rows.length === 0 ? (
            <div className="p-12 text-center text-sm text-muted-foreground">
              No audit events match this filter.
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>When</TableHead>
                  <TableHead>Action</TableHead>
                  <TableHead>Target</TableHead>
                  <TableHead>Source</TableHead>
                  <TableHead>Actor</TableHead>
                  <TableHead>Request ID</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {rows.map((r) => (
                  <TableRow key={r.id}>
                    <TableCell className="font-mono text-xs whitespace-nowrap">
                      {formatDate(r.occurred_at)}
                    </TableCell>
                    <TableCell>
                      <Badge variant="outline" className="font-mono text-xs">
                        {r.action}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      <span className="text-muted-foreground capitalize mr-2">
                        {r.target_kind}
                      </span>
                      {r.target_id ? (
                        <span className="font-mono text-xs">{r.target_id.slice(0, 8)}</span>
                      ) : null}
                    </TableCell>
                    <TableCell>
                      <Badge variant="secondary" className="capitalize">
                        {r.source}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-muted-foreground text-xs">
                      {r.actor_user_id ? r.actor_user_id.slice(0, 8) : r.actor_label ?? "system"}
                    </TableCell>
                    <TableCell className="font-mono text-xs text-muted-foreground">
                      {r.request_id ? r.request_id.slice(0, 8) : "—"}
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
