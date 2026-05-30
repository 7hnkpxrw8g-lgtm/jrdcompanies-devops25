"use client";

import { Upload } from "lucide-react";
import { useRef, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { useToast } from "@/components/ui/toast";
import { API_BASE } from "@/lib/api";

export function CsvImportButton({ bankAccountId }: { bankAccountId: string }) {
  const inputRef = useRef<HTMLInputElement>(null);
  const { toast } = useToast();
  const qc = useQueryClient();
  const [uploading, setUploading] = useState(false);

  async function onPick(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true);
    try {
      const form = new FormData();
      form.append("file", file);
      const token = window.localStorage.getItem("jrd_token");
      const r = await fetch(
        `${API_BASE}/imports/bank-csv?bank_account_id=${bankAccountId}`,
        {
          method: "POST",
          headers: token ? { Authorization: `Bearer ${token}` } : undefined,
          body: form,
        }
      );
      const body = (await r.json()) as {
        imported?: number;
        skipped_duplicates?: number;
        ai_suggestions?: number;
        errors?: string[];
        detail?: string;
      };
      if (!r.ok) {
        toast({
          variant: "destructive",
          title: "Import failed",
          description: body.detail ?? "Unknown error",
        });
        return;
      }
      toast({
        variant: "success",
        title: `Imported ${body.imported} transactions`,
        description: `${body.skipped_duplicates} skipped · ${body.ai_suggestions} AI-categorized`,
      });
      qc.invalidateQueries({ queryKey: ["bank-tx"] });
      qc.invalidateQueries({ queryKey: ["recon-tx"] });
    } finally {
      setUploading(false);
      if (inputRef.current) inputRef.current.value = "";
    }
  }

  return (
    <>
      <input
        ref={inputRef}
        type="file"
        accept=".csv,text/csv"
        className="hidden"
        onChange={onPick}
      />
      <Button
        variant="outline"
        size="sm"
        disabled={uploading}
        onClick={() => inputRef.current?.click()}
      >
        <Upload className="h-3.5 w-3.5" />
        {uploading ? "Uploading…" : "Import CSV"}
      </Button>
    </>
  );
}
