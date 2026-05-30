"use client";

import { useMutation, useQuery } from "@tanstack/react-query";
import { Plus, Trash2 } from "lucide-react";
import { useRouter } from "next/navigation";
import { useMemo, useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { apiClient } from "@/lib/api";
import { useAppStore } from "@/lib/store";
import type { Account, Vendor } from "@/lib/types";
import { formatCurrency } from "@/lib/utils";

interface DraftLine {
  description: string;
  amount: string;
  expense_account_id: string;
}

const blank: DraftLine = { description: "", amount: "", expense_account_id: "" };

export default function NewBillPage() {
  const router = useRouter();
  const activeEntityId = useAppStore((s) => s.activeEntityId);
  const today = new Date().toISOString().slice(0, 10);
  const dueDefault = new Date(Date.now() + 30 * 86400000).toISOString().slice(0, 10);

  const [vendorId, setVendorId] = useState("");
  const [issueDate, setIssueDate] = useState(today);
  const [dueDate, setDueDate] = useState(dueDefault);
  const [lines, setLines] = useState<DraftLine[]>([{ ...blank }]);
  const [notes, setNotes] = useState("");
  const [error, setError] = useState<string | null>(null);

  const { data: vendors } = useQuery({
    queryKey: ["vendors"],
    queryFn: () => apiClient.get<Vendor[]>("/vendors"),
  });
  const { data: accounts } = useQuery({
    queryKey: ["accounts", activeEntityId],
    queryFn: () => apiClient.get<Account[]>(`/accounts?entity_id=${activeEntityId}`),
    enabled: !!activeEntityId,
  });

  const expenseAccounts = (accounts ?? []).filter((a) => a.type === "expense");
  const total = useMemo(
    () => lines.reduce((s, l) => s + (Number(l.amount) || 0), 0),
    [lines]
  );

  const submit = useMutation({
    mutationFn: (approve: boolean) => {
      if (!activeEntityId) throw new Error("No active entity");
      if (!vendorId) throw new Error("Pick a vendor");
      return apiClient.post(`/bills?approve=${approve}`, {
        entity_id: activeEntityId,
        vendor_id: vendorId,
        issue_date: issueDate,
        due_date: dueDate,
        currency: "USD",
        notes,
        lines: lines.map((l, i) => ({
          line_no: i + 1,
          expense_account_id: l.expense_account_id || expenseAccounts[0]?.id,
          description: l.description || "Bill line",
          amount: l.amount || "0",
        })),
      });
    },
    onSuccess: () => router.push("/app/bills"),
    onError: (err) => setError(err instanceof Error ? err.message : "Could not save bill"),
  });

  return (
    <div className="space-y-5 max-w-4xl">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">New bill</h1>
        <p className="text-sm text-muted-foreground">
          Approving posts an AP + expense journal automatically.
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Header</CardTitle>
          <CardDescription>Vendor, dates, notes.</CardDescription>
        </CardHeader>
        <CardContent className="grid gap-4 md:grid-cols-3">
          <div className="space-y-1.5 md:col-span-2">
            <label className="text-sm font-medium">Vendor</label>
            <select
              className="h-9 w-full rounded-md border bg-background px-2 text-sm focus-ring"
              value={vendorId}
              onChange={(e) => setVendorId(e.target.value)}
            >
              <option value="">Select vendor</option>
              {(vendors ?? []).map((v) => (
                <option key={v.id} value={v.id}>{v.display_name}</option>
              ))}
            </select>
          </div>
          <div className="space-y-1.5">
            <label className="text-sm font-medium">Issue date</label>
            <Input type="date" value={issueDate} onChange={(e) => setIssueDate(e.target.value)} />
          </div>
          <div className="space-y-1.5">
            <label className="text-sm font-medium">Due date</label>
            <Input type="date" value={dueDate} onChange={(e) => setDueDate(e.target.value)} />
          </div>
          <div className="space-y-1.5 md:col-span-2">
            <label className="text-sm font-medium">Notes</label>
            <Input value={notes} onChange={(e) => setNotes(e.target.value)} placeholder="Internal notes" />
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle>Lines</CardTitle>
              <CardDescription>Each line books to an expense account.</CardDescription>
            </div>
            <Button variant="outline" size="sm" onClick={() => setLines((p) => [...p, { ...blank }])}>
              <Plus className="h-4 w-4" /> Add
            </Button>
          </div>
        </CardHeader>
        <CardContent className="p-0">
          <table className="w-full text-sm">
            <thead className="border-b text-xs uppercase tracking-wide text-muted-foreground">
              <tr>
                <th className="py-2 px-3 text-left">Description</th>
                <th className="py-2 px-3 text-left">Expense account</th>
                <th className="py-2 px-3 text-right">Amount</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {lines.map((l, i) => (
                <tr key={i} className="border-b last:border-0">
                  <td className="py-2 px-3 min-w-[20rem]">
                    <Input
                      value={l.description}
                      onChange={(e) =>
                        setLines((p) =>
                          p.map((r, idx) => (idx === i ? { ...r, description: e.target.value } : r))
                        )
                      }
                    />
                  </td>
                  <td className="py-2 px-3 min-w-[200px]">
                    <select
                      className="h-9 w-full rounded-md border bg-background px-2 text-sm"
                      value={l.expense_account_id}
                      onChange={(e) =>
                        setLines((p) =>
                          p.map((r, idx) =>
                            idx === i ? { ...r, expense_account_id: e.target.value } : r
                          )
                        )
                      }
                    >
                      <option value="">Pick…</option>
                      {expenseAccounts.map((a) => (
                        <option key={a.id} value={a.id}>{a.code} — {a.name}</option>
                      ))}
                    </select>
                  </td>
                  <td className="py-2 px-3 w-32">
                    <Input
                      type="number"
                      step="0.01"
                      className="text-right tabular"
                      value={l.amount}
                      onChange={(e) =>
                        setLines((p) =>
                          p.map((r, idx) => (idx === i ? { ...r, amount: e.target.value } : r))
                        )
                      }
                    />
                  </td>
                  <td className="py-2 px-3 w-10">
                    <Button
                      variant="ghost"
                      size="icon"
                      onClick={() =>
                        setLines((p) => (p.length > 1 ? p.filter((_, idx) => idx !== i) : p))
                      }
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </td>
                </tr>
              ))}
            </tbody>
            <tfoot className="bg-accent/30 font-semibold">
              <tr>
                <td colSpan={2} className="py-2 px-3 text-right uppercase">Total</td>
                <td className="py-2 px-3 text-right tabular">{formatCurrency(total)}</td>
                <td />
              </tr>
            </tfoot>
          </table>
        </CardContent>
      </Card>

      <div className="flex items-center justify-end gap-2">
        {error ? <span className="text-sm text-destructive">{error}</span> : null}
        <Button variant="outline" disabled={submit.isPending} onClick={() => submit.mutate(false)}>
          Save draft
        </Button>
        <Button disabled={submit.isPending} onClick={() => submit.mutate(true)}>
          Approve & post
        </Button>
      </div>
    </div>
  );
}
