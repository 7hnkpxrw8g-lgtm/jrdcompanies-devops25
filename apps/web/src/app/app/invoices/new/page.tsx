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
import type { Account, Customer, Invoice } from "@/lib/types";
import { formatCurrency } from "@/lib/utils";

interface DraftLine {
  description: string;
  quantity: string;
  unit_price: string;
  tax_rate: string;
  revenue_account_id: string;
}

const blank: DraftLine = { description: "", quantity: "1", unit_price: "0", tax_rate: "0", revenue_account_id: "" };

export default function NewInvoicePage() {
  const router = useRouter();
  const activeEntityId = useAppStore((s) => s.activeEntityId);
  const today = new Date().toISOString().slice(0, 10);
  const dueDefault = new Date(Date.now() + 30 * 86400000).toISOString().slice(0, 10);

  const [customerId, setCustomerId] = useState("");
  const [issueDate, setIssueDate] = useState(today);
  const [dueDate, setDueDate] = useState(dueDefault);
  const [lines, setLines] = useState<DraftLine[]>([{ ...blank }]);
  const [notes, setNotes] = useState("");
  const [error, setError] = useState<string | null>(null);

  const { data: customers } = useQuery({
    queryKey: ["customers"],
    queryFn: () => apiClient.get<Customer[]>("/customers"),
  });
  const { data: accounts } = useQuery({
    queryKey: ["accounts", activeEntityId],
    queryFn: () => apiClient.get<Account[]>(`/accounts?entity_id=${activeEntityId}`),
    enabled: !!activeEntityId,
  });

  const revenueAccounts = (accounts ?? []).filter((a) =>
    a.type === "revenue" || a.type === "contra_revenue"
  );

  const totals = useMemo(() => {
    let subtotal = 0;
    let tax = 0;
    for (const l of lines) {
      const lineSubtotal = (Number(l.quantity) || 0) * (Number(l.unit_price) || 0);
      const lineTax = lineSubtotal * (Number(l.tax_rate) || 0);
      subtotal += lineSubtotal;
      tax += lineTax;
    }
    return { subtotal, tax, total: subtotal + tax };
  }, [lines]);

  const submit = useMutation({
    mutationFn: async (approve: boolean) => {
      if (!activeEntityId) throw new Error("No active entity");
      if (!customerId) throw new Error("Pick a customer");
      const payload = {
        entity_id: activeEntityId,
        customer_id: customerId,
        issue_date: issueDate,
        due_date: dueDate,
        currency: "USD",
        notes,
        lines: lines.map((l, i) => ({
          line_no: i + 1,
          revenue_account_id: l.revenue_account_id || revenueAccounts[0]?.id,
          description: l.description || "Item",
          quantity: l.quantity || "1",
          unit_price: l.unit_price || "0",
          tax_rate: l.tax_rate || "0",
          discount_amount: "0",
          kind: "service",
        })),
      };
      return apiClient.post<Invoice>(`/invoices?approve=${approve}`, payload);
    },
    onSuccess: () => router.push("/app/invoices"),
    onError: (err) => setError(err instanceof Error ? err.message : "Could not save invoice"),
  });

  return (
    <div className="space-y-5 max-w-4xl">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">New invoice</h1>
        <p className="text-sm text-muted-foreground">
          Approving posts AR + revenue journals automatically.
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Header</CardTitle>
          <CardDescription>Customer, dates, notes.</CardDescription>
        </CardHeader>
        <CardContent className="grid gap-4 md:grid-cols-3">
          <div className="space-y-1.5 md:col-span-2">
            <label className="text-sm font-medium">Customer</label>
            <select
              className="h-9 w-full rounded-md border bg-background px-2 text-sm focus-ring"
              value={customerId}
              onChange={(e) => setCustomerId(e.target.value)}
            >
              <option value="">Select customer</option>
              {(customers ?? []).map((c) => (
                <option key={c.id} value={c.id}>{c.display_name}</option>
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
            <Input value={notes} onChange={(e) => setNotes(e.target.value)} placeholder="Visible on the invoice PDF" />
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle>Lines</CardTitle>
              <CardDescription>One row per item / service.</CardDescription>
            </div>
            <Button variant="outline" size="sm" onClick={() => setLines((p) => [...p, { ...blank }])}>
              <Plus className="h-4 w-4" /> Add
            </Button>
          </div>
        </CardHeader>
        <CardContent className="p-0">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="border-b text-xs uppercase tracking-wide text-muted-foreground">
                <tr>
                  <th className="py-2 px-3 text-left">Description</th>
                  <th className="py-2 px-3 text-left">Revenue acct</th>
                  <th className="py-2 px-3 text-right">Qty</th>
                  <th className="py-2 px-3 text-right">Unit</th>
                  <th className="py-2 px-3 text-right">Tax</th>
                  <th className="py-2 px-3 text-right">Total</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {lines.map((l, i) => {
                  const lineSub = (Number(l.quantity) || 0) * (Number(l.unit_price) || 0);
                  return (
                    <tr key={i} className="border-b last:border-0">
                      <td className="py-2 px-3 min-w-[16rem]">
                        <Input value={l.description} onChange={(e) => setLines((p) => p.map((row, idx) => idx === i ? { ...row, description: e.target.value } : row))} />
                      </td>
                      <td className="py-2 px-3 min-w-[180px]">
                        <select
                          className="h-9 w-full rounded-md border bg-background px-2 text-sm"
                          value={l.revenue_account_id}
                          onChange={(e) =>
                            setLines((p) => p.map((row, idx) => idx === i ? { ...row, revenue_account_id: e.target.value } : row))
                          }
                        >
                          <option value="">Pick…</option>
                          {revenueAccounts.map((a) => (
                            <option key={a.id} value={a.id}>{a.code} — {a.name}</option>
                          ))}
                        </select>
                      </td>
                      <td className="py-2 px-3 w-24">
                        <Input type="number" step="0.01" className="text-right tabular" value={l.quantity}
                          onChange={(e) => setLines((p) => p.map((r, idx) => idx === i ? { ...r, quantity: e.target.value } : r))} />
                      </td>
                      <td className="py-2 px-3 w-28">
                        <Input type="number" step="0.01" className="text-right tabular" value={l.unit_price}
                          onChange={(e) => setLines((p) => p.map((r, idx) => idx === i ? { ...r, unit_price: e.target.value } : r))} />
                      </td>
                      <td className="py-2 px-3 w-24">
                        <Input type="number" step="0.0001" className="text-right tabular" value={l.tax_rate}
                          onChange={(e) => setLines((p) => p.map((r, idx) => idx === i ? { ...r, tax_rate: e.target.value } : r))} />
                      </td>
                      <td className="py-2 px-3 text-right tabular font-medium">{formatCurrency(lineSub)}</td>
                      <td className="py-2 px-3 w-10">
                        <Button variant="ghost" size="icon" onClick={() => setLines((p) => p.length > 1 ? p.filter((_, idx) => idx !== i) : p)}>
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
              <tfoot className="bg-accent/30">
                <tr><td colSpan={5} className="py-2 px-3 text-right text-muted-foreground">Subtotal</td><td className="py-2 px-3 text-right tabular">{formatCurrency(totals.subtotal)}</td><td /></tr>
                <tr><td colSpan={5} className="py-2 px-3 text-right text-muted-foreground">Tax</td><td className="py-2 px-3 text-right tabular">{formatCurrency(totals.tax)}</td><td /></tr>
                <tr className="font-semibold"><td colSpan={5} className="py-2 px-3 text-right uppercase">Total</td><td className="py-2 px-3 text-right tabular">{formatCurrency(totals.total)}</td><td /></tr>
              </tfoot>
            </table>
          </div>
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
