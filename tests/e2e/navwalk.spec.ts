import { expect, test } from "@playwright/test";

const PAGES = [
  "/app", "/app/banking", "/app/reconciliation", "/app/transactions",
  "/app/ledger", "/app/reports", "/app/invoices", "/app/bills",
  "/app/customers", "/app/vendors", "/app/inventory", "/app/fuel",
  "/app/repair-orders", "/app/payroll", "/app/ai", "/app/integrations",
  "/app/audit", "/app/settings",
];

test("every nav page renders an h1 with no console errors", async ({ page }) => {
  const errors: Record<string, string[]> = {};
  page.on("console", (m) => {
    if (m.type() === "error") {
      const u = page.url();
      (errors[u] ??= []).push(m.text());
    }
  });

  await page.goto("/login");
  await page.getByLabel(/email/i).fill("demo@jrdbooks.io");
  await page.getByLabel(/password/i).fill("demo");
  await page.getByRole("button", { name: /sign in/i }).click();
  await expect(page).toHaveURL(/\/app/, { timeout: 10000 });

  const broken: string[] = [];
  for (const path of PAGES) {
    await page.goto(path, { waitUntil: "domcontentloaded" });
    await page.waitForTimeout(700);
    const h1 = await page.locator("h1").first().textContent().catch(() => null);
    if (!h1 || h1.trim().length === 0) broken.push(`${path}: no h1`);
  }
  console.log("BROKEN:", broken.length ? broken.join(" ; ") : "none");
  expect(broken).toEqual([]);
});
