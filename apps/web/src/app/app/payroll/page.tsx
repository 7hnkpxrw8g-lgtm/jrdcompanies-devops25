import { EmptyModule } from "@/components/app/empty-module";

export default function PayrollPage() {
  return (
    <EmptyModule
      title="Payroll"
      description="Payroll runs, payslips, employer + employee taxes, GL booking."
      apiPath="/payroll"
      bullets={[
        "payroll_run + payslip schema; gross/net/taxes captured.",
        "Approval posts a journal: wages (Dr), payroll taxes (Dr), bank/clearing (Cr).",
        "Integrates with provider webhooks (Gusto, ADP) when configured.",
      ]}
    />
  );
}
