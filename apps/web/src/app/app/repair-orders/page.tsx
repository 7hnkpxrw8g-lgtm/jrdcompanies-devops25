import { EmptyModule } from "@/components/app/empty-module";

export default function RepairOrdersPage() {
  return (
    <EmptyModule
      title="Repair orders"
      description="Vehicle ROs (Tekmetric import or manual), labor + parts, invoice handoff."
      apiPath="/repair-orders"
      bullets={[
        "repair_order header + lines (kind = labor|part|fee).",
        "Closing an RO creates the customer invoice and posts AR + revenue journals.",
        "Optional Tekmetric integration drops in via external_id.",
      ]}
    />
  );
}
