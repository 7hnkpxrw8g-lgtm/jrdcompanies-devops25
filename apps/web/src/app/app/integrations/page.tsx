"use client";

import { Banknote, Building, Cloud, CreditCard, Mail, ShoppingBag, Wrench } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

const PROVIDERS = [
  { name: "Plaid", icon: Banknote, desc: "Bank account aggregation & transactions.", category: "Banking" },
  { name: "Stripe", icon: CreditCard, desc: "Payment processing, payouts, refunds.", category: "Payments" },
  { name: "Square", icon: ShoppingBag, desc: "POS payouts, transaction sync.", category: "Payments" },
  { name: "Coinbase", icon: Cloud, desc: "Crypto holdings + tx history.", category: "Payments" },
  { name: "Tekmetric", icon: Wrench, desc: "Auto-shop management; pulls ROs & invoices.", category: "Operations" },
  { name: "Shopify", icon: ShoppingBag, desc: "E-commerce orders, payouts, inventory.", category: "Commerce" },
  { name: "Gmail", icon: Mail, desc: "Bill / receipt extraction from email.", category: "Documents" },
  { name: "Outlook", icon: Mail, desc: "Bill / receipt extraction from email.", category: "Documents" },
  { name: "QuickBooks", icon: Building, desc: "One-time import or ongoing sync.", category: "Migration" },
];

export default function IntegrationsPage() {
  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Integrations</h1>
        <p className="text-sm text-muted-foreground">
          Connect external systems. Each provider supports OAuth, webhooks, idempotent ingestion,
          and a sync history surfaced in this UI.
        </p>
      </div>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {PROVIDERS.map((p) => {
          const Icon = p.icon;
          return (
            <Card key={p.name}>
              <CardHeader>
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <div className="grid h-8 w-8 place-items-center rounded-md bg-accent">
                      <Icon className="h-4 w-4" />
                    </div>
                    <CardTitle className="text-base">{p.name}</CardTitle>
                  </div>
                  <Badge variant="outline">{p.category}</Badge>
                </div>
              </CardHeader>
              <CardContent className="space-y-3">
                <CardDescription>{p.desc}</CardDescription>
                <div className="flex items-center gap-2">
                  <Button size="sm" variant="outline">Connect</Button>
                  <span className="text-xs text-muted-foreground">Sandbox creds available</span>
                </div>
              </CardContent>
            </Card>
          );
        })}
      </div>
    </div>
  );
}
