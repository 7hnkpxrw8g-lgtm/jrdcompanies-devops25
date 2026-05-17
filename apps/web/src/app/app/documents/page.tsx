import { EmptyModule } from "@/components/app/empty-module";

export default function DocumentsPage() {
  return (
    <EmptyModule
      title="Documents"
      description="Receipts, bills, contracts — extracted and linked to ledger rows."
      apiPath="/documents"
      bullets={[
        "Storage layer = S3-compatible; per-org bucket key prefix.",
        "OCR + LLM extraction proposes a draft journal you can post in one click.",
        "Inbox + history views with full-text search.",
      ]}
    />
  );
}
