"use client";

import { useQuery } from "@tanstack/react-query";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { apiClient } from "@/lib/api";
import type { Vendor } from "@/lib/types";

export default function VendorsPage() {
  const { data, isLoading } = useQuery({
    queryKey: ["vendors"],
    queryFn: () => apiClient.get<Vendor[]>("/vendors"),
  });

  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Vendors</h1>
        <p className="text-sm text-muted-foreground">
          Suppliers you pay. 1099 status is tracked here for year-end reporting.
        </p>
      </div>
      <Card>
        <CardHeader>
          <CardTitle>{data?.length ?? 0} vendors</CardTitle>
          <CardDescription>Editing flows will move into this table.</CardDescription>
        </CardHeader>
        <CardContent className="p-0">
          {isLoading ? (
            <div className="p-6 space-y-2">
              {Array.from({ length: 4 }).map((_, i) => (
                <Skeleton key={i} className="h-8 w-full" />
              ))}
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Code</TableHead>
                  <TableHead>Name</TableHead>
                  <TableHead>Email</TableHead>
                  <TableHead>Terms</TableHead>
                  <TableHead>1099?</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {(data ?? []).map((v) => (
                  <TableRow key={v.id}>
                    <TableCell className="font-mono text-xs">{v.code}</TableCell>
                    <TableCell className="font-medium">{v.display_name}</TableCell>
                    <TableCell className="text-muted-foreground">{v.email ?? "—"}</TableCell>
                    <TableCell>Net {v.default_terms_days}</TableCell>
                    <TableCell>
                      {v.is_1099 ? (
                        <Badge variant="warning">1099</Badge>
                      ) : (
                        <span className="text-muted-foreground text-xs">—</span>
                      )}
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
