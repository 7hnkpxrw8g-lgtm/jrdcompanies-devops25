"use client";

import { Sparkles, Send } from "lucide-react";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";

export default function AiPage() {
  const [prompt, setPrompt] = useState("");
  return (
    <div className="space-y-5 max-w-3xl">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">AI assistant</h1>
        <p className="text-sm text-muted-foreground">
          Ask about your books. Responses are grounded in your ledger — every claim cites the source
          journal or report.
        </p>
      </div>

      <Card className="bg-gradient-to-br from-primary/5 to-transparent">
        <CardHeader>
          <div className="flex items-center gap-2">
            <Sparkles className="h-4 w-4 text-primary" />
            <CardTitle>Try these prompts</CardTitle>
          </div>
          <CardDescription>The assistant is GAAP-aware and never fabricates numbers.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-2 text-sm">
          {[
            "Explain why net income dropped in April vs March.",
            "List every uncategorized bank transaction over $500.",
            "Summarize fuel variance for JRD-FUEL last month.",
            "Suggest a journal to reclass the May rent expense to prepaid rent.",
          ].map((s) => (
            <button
              key={s}
              className="block w-full rounded-md border bg-card px-3 py-2 text-left hover:border-primary/40 hover:shadow-sm transition"
              onClick={() => setPrompt(s)}
            >
              {s}
            </button>
          ))}
        </CardContent>
      </Card>

      <Card>
        <CardContent className="p-4">
          <div className="flex items-center gap-2">
            <Input
              placeholder="Ask the assistant…"
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
            />
            <Button>
              <Send className="h-4 w-4" /> Send
            </Button>
          </div>
          <p className="mt-2 text-xs text-muted-foreground">
            Backed by your configured AI model. Tool-use lets it query the ledger directly — no
            hallucinated dollars.
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
