import { EmptyModule } from "@/components/app/empty-module";

export default function AuditPage() {
  return (
    <EmptyModule
      title="Audit logs"
      description="Append-only event stream — every API write produces an entry."
      apiPath="/audit"
      bullets={[
        "audit_event captures actor, source, request_id, before/after diff.",
        "Filter by target_kind (journal, invoice, integration), org, entity.",
        "Compliance export: CSV + JSON download endpoints.",
      ]}
    />
  );
}
