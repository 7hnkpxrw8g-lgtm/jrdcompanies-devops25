import { EmptyModule } from "@/components/app/empty-module";

export default function InventoryPage() {
  return (
    <EmptyModule
      title="Inventory"
      description="SKUs, weighted-average cost, stock lots, and movements that auto-journal."
      apiPath="/inventory"
      bullets={[
        "inventory_item, stock_lot, and inventory_movement tables wired with weighted-avg cost.",
        "Each movement posts to inventory_account and cogs_account_id.",
        "Valuation report aggregates on_hand × avg_cost per item.",
      ]}
    />
  );
}
