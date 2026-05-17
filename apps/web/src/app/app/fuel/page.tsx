import { EmptyModule } from "@/components/app/empty-module";

export default function FuelPage() {
  return (
    <EmptyModule
      title="Fuel operations"
      description="Tank levels, deliveries, dispenses, and stick-reading variance."
      apiPath="/fuel"
      bullets={[
        "fuel_tank tracks capacity, current volume, weighted-average cost.",
        "fuel_delivery posts to inventory; fuel_dispense posts COGS and revenue.",
        "Variance = stick reading − calculated; auto-posts shrinkage when out of tolerance.",
      ]}
    />
  );
}
