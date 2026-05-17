"use client";

import { useMutation, useQuery } from "@tanstack/react-query";
import { Plus, Save, Trash2 } from "lucide-react";
import { useRouter } from "next/navigation";
import { useMemo, useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { apiClient } from "@/lib/api";
import { useAppStore } from "@/lib/store";
import type { Account, Journal } from "@/lib/types";
import { cn, formatCurrency } from "@/lib/utils";

interface DraftLine {
  account_id: string;
  debit: string;
  credit: string;
  description: string;
}

const blankLine: DraftLine = { account_id: "", debit: "", credit: "", description: "" };

export default function NewTransactionPage() {
  const router = useRouter();
  const activeEntityId = useAppStore((s) => s.activeEntityId);
  const today = new Date().toISOString().slice(0, 10);

  const [postingDate, setPostingDate] = useState(today);
  const [memo, setMemo] = useState("");
  const [lines, setLines] = useState<DraftLine[]>([{ ...blankLine }, { ...blankLine }]);
  const [error, setError] = useState<string | null>(null);

  const { data: accounts } = useQuery({
    queryKey: ["accounts", activeEntityId],
    queryFn: () =>
      apiClient.get<Account[]>(`/accounts?entity_id=${activeEntityId}`),
    enabled: !!activeEntityId,
  });

  const totals = useMemo(() => {
    const d = lines.reduce((s, l) => s + (Number.parseFloat(l.debit) || 0), 0);
    const c = lines.reduce((s, l) => s + (Number.parseFloat(l.credit) || 0), 0);
    return { d, c, delta: d - c };
  }, [lines]);

  const create = useMutation({
    mutationFn: async (post: boolean) => {
      if (!activeEntityId) throw new Error("Select an entity first");
      const payload = {
        entity_id: activeEntityId,
        posting_date: postingDate,
        memo,
        currency: "USD",
        lines: lines
          .filter((l) => l.account_id)
          .map((l, i) => ({
            line_no: i + 1,
            account_id: l.account_id,
            debit: l.debit || "0",
            credit: l.credit || "0",
            description: l.description || null,
          })),
      };
      return apiClient.post<Journal>(`/journals?post=${post}`, payload);
    },
    onSuccess: (data) => {
      router.push(`/app/transactions/${data.id}`);
    },
    onError: (err) => {
      setError(err instanceof Error ? err.message : "Failed to save");
    },
  });

  function updateLine(i: number, patch: Partial<DraftLine>) {
    setLines((prev) => prev.map((l, idx) => (idx === i ? { ...l, ...patch } : l)));
  }

  function balanced() {
    return Math.abs(totals.delta) < 0.005 && totals.d > 0;
  }

  return (
    <div className="max-w-5xl space-y-5">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">New journal entry</h1>
        <p className="text-sm text-muted-foreground">
          Debits must equal credits. Draft a journal first, then post when ready.
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Header</CardTitle>
          <CardDescription>Posting date and memo are required.</CardDescription>
        </CardHeader>
        <CardContent className="grid gap-4 md:grid-cols-2">
          <div className="space-y-1.5">
            <label className="text-sm font-medium">Posting date</label>
            <Input
              type="date"
              value={postingDate}
              onChange={(e) => setPostingDate(e.target.value)}
            />
          </div>
          <div className="space-y-1.5">
            <label className="text-sm font-medium">Memo</label>
            <Input
              placeholder="e.g. May rent payment"
              value={memo}
              onChange={(e) => setMemo(e.target.value)}
            />
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle>Lines</CardTitle>
              <CardDescription>
                Use debits on the left, credits on the right. The totals must match.
              </CardDescription>
            </div>
            <Button
              size="sm"
              variant="outline"
              onClick={() => setLines((p) => [...p, { ...blankLine }])}
            >
              <Plus className="h-4 w-4" /> Add line
            </Button>
          </div>
        </CardHeader>
        <CardContent className="p-0">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="border-b">
                <tr className="text-xs uppercase tracking-wide text-muted-foreground">
                  <th className="py-2 px-3 text-left">#</th>
                  <th className="py-2 px-3 text-left">Account</th>
                  <th className="py-2 px-3 text-left">Description</th>
                  <th className="py-2 px-3 text-right">Debit</th>
                  <th className="py-2 px-3 text-right">Credit</th>
                  <th className="py-2 px-3" />
                </tr>
              </thead>
              <tbody>
                {lines.map((line, i) => (
                  <tr key={i} className="border-b last:border-0">
                    <td className="py-2 px-3 text-xs text-muted-foreground tabular">{i + 1}</td>
                    <td className="py-2 px-3 min-w-[260px]">
                      <select
                        className="h-9 w-full rounded-md border bg-background px-2 text-sm focus-ring"
                        value={line.account_id}
                        onChange={(e) => updateLine(i, { account_id: e.target.value })}
                      >
                        <option value="">Select account</option>
                        {(accounts ?? []).map((a) => (
                          <option key={a.id} value={a.id}>
                            {a.code} — {a.name}
                          </option>
                        ))}
                      </select>
                    </td>
                    <td className="py-2 px-3">
                      <Input
                        placeholder="Optional description"
                        value={line.description}
                        onChange={(e) => updateLine(i, { description: e.target.value })}
                      />
                    </td>
                    <td className="py-2 px-3 w-[140px]">
                      <Input
                        type="number"
                        step="0.01"
                        className="text-right tabular"
                        value={line.debit}
                        onChange={(e) =>
                          updateLine(i, {
                            debit: e.target.value,
                            credit: e.target.value ? "" : line.credit,
                          })
                        }
                      />
                    </td>
                    <td className="py-2 px-3 w-[140px]">
                      <Input
                        type="number"
                        step="0.01"
                        className="text-right tabular"
                        value={line.credit}
                        onChange={(e) =>
                          updateLine(i, {
                            credit: e.target.value,
                            debit: e.target.value ? "" : line.debit,
                          })
                        }
                      />
                    </td>
                    <td className="py-2 px-3 w-10">
                      <Button
                        variant="ghost"
                        size="icon"
                        onClick={() =>
                          setLines((p) => (p.length > 2 ? p.filter((_, idx) => idx !== i) : p))
                        }
                      >
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
              <tfoot>
                <tr className="bg-accent/40 font-medium">
                  <td colSpan={3} className="py-3 px-3 text-right text-muted-foreground">
                    Totals
                  </td>
                  <td className="py-3 px-3 text-right tabular">{formatCurrency(totals.d)}</td>
                  <td className="py-3 px-3 text-right tabular">{formatCurrency(totals.c)}</td>
                  <td />
                </tr>
              </tfoot>
            </table>
          </div>
        </CardContent>
      </Card>

      <div className="flex items-center justify-between gap-3">
        <Badge variant={balanced() ? "success" : "warning"} className={cn("text-xs")}>
          {balanced() ? "Balanced" : `Off by ${formatCurrency(totals.delta)}`}
        </Badge>
        <div className="flex items-center gap-2">
          {error ? <span className="text-sm text-destructive">{error}</span> : null}
          <Button
            variant="outline"
            disabled={create.isPending}
            onClick={() => create.mutate(false)}
          >
            <Save className="h-4 w-4" /> Save draft
          </Button>
          <Button
            disabled={!balanced() || create.isPending}
            onClick={() => create.mutate(true)}
          >
            Post journal
          </Button>
        </div>
      </div>
    </div>
  );
}
