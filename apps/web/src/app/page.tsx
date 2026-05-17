import Link from "next/link";
import { ArrowRight, LineChart, Lock, Sparkles, Banknote } from "lucide-react";
import { Button } from "@/components/ui/button";

export default function HomePage() {
  return (
    <main className="min-h-screen bg-gradient-to-b from-background to-accent/40">
      <header className="border-b border-border/60 backdrop-blur-md sticky top-0 z-10 bg-background/70">
        <div className="container flex h-14 items-center justify-between">
          <div className="flex items-center gap-2 font-semibold tracking-tight">
            <div className="h-7 w-7 rounded-md bg-primary text-primary-foreground grid place-items-center text-xs font-bold">
              JR
            </div>
            JRDbooks
          </div>
          <nav className="flex items-center gap-4 text-sm">
            <Link href="/login" className="text-muted-foreground hover:text-foreground">
              Sign in
            </Link>
            <Button asChild size="sm">
              <Link href="/login">
                Open dashboard <ArrowRight className="h-4 w-4" />
              </Link>
            </Button>
          </nav>
        </div>
      </header>

      <section className="container py-24">
        <div className="mx-auto max-w-3xl text-center">
          <div className="inline-flex items-center gap-1.5 rounded-full border border-border bg-background px-3 py-1 text-xs font-medium text-muted-foreground">
            <Sparkles className="h-3 w-3" /> Multi-entity accounting, finally clean
          </div>
          <h1 className="mt-6 text-5xl font-semibold tracking-tight md:text-6xl">
            The accounting platform <br />
            <span className="text-primary">your bookkeeper deserves.</span>
          </h1>
          <p className="mt-6 text-lg text-muted-foreground">
            Double-entry. Real-time reconciliation. AI-assisted categorization. Audit-grade history.
            Built for operators running multiple entities — fuel ops, repair shops, and everything else.
          </p>
          <div className="mt-10 flex items-center justify-center gap-3">
            <Button asChild size="lg">
              <Link href="/login">Open the demo</Link>
            </Button>
            <Button asChild size="lg" variant="outline">
              <a href="https://github.com/" target="_blank" rel="noreferrer">View architecture</a>
            </Button>
          </div>
        </div>

        <div className="mx-auto mt-24 grid max-w-5xl grid-cols-1 gap-6 md:grid-cols-3">
          <Feature icon={<LineChart className="h-5 w-5" />} title="Reports that actually tie">
            P&L, balance sheet, cash flow, trial balance — all generated from the same immutable ledger.
            The numbers always reconcile because there is only one source of truth.
          </Feature>
          <Feature icon={<Banknote className="h-5 w-5" />} title="Bank-grade reconciliation">
            Plaid, Stripe, Square, Coinbase. AI proposes categorizations with a confidence score; you
            click to post. Reconciliation queue clears in minutes, not days.
          </Feature>
          <Feature icon={<Lock className="h-5 w-5" />} title="Audit-grade history">
            Posted journals are immutable. Reversals create new entries. Every change writes an audit
            event with actor, source, request ID, and full before/after diff.
          </Feature>
        </div>
      </section>

      <footer className="border-t border-border/60 py-8 text-center text-sm text-muted-foreground">
        <p>© 2026 JRDbooks · Built with FastAPI, Next.js, and Postgres.</p>
      </footer>
    </main>
  );
}

function Feature({ icon, title, children }: { icon: React.ReactNode; title: string; children: React.ReactNode }) {
  return (
    <div className="rounded-xl border bg-card p-6 shadow-sm">
      <div className="grid h-9 w-9 place-items-center rounded-lg bg-primary/10 text-primary">{icon}</div>
      <h3 className="mt-4 font-semibold">{title}</h3>
      <p className="mt-2 text-sm text-muted-foreground">{children}</p>
    </div>
  );
}
