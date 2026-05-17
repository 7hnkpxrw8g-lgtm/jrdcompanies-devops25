import { EmptyModule } from "@/components/app/empty-module";

export default function BillsPage() {
  return (
    <EmptyModule
      title="Bills"
      description="Vendor bills, approval, and AP aging. Approval posts AP + expense journals."
      apiPath="/bills"
      bullets={[
        "Schema in place (bill, journal source = bill).",
        "Approval workflow: pending → approved → paid (mirrors invoice flow).",
        "AP aging report computed from outstanding bills.",
      ]}
    />
  );
}
