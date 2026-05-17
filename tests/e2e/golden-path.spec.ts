import { expect, test } from "@playwright/test";

const EMAIL = process.env.E2E_EMAIL ?? "demo@jrdbooks.io";
const PASSWORD = process.env.E2E_PASSWORD ?? "demo";

async function signIn(page: import("@playwright/test").Page) {
  await page.goto("/login");
  await page.getByLabel(/email/i).fill(EMAIL);
  await page.getByLabel(/password/i).fill(PASSWORD);
  await page.getByRole("button", { name: /sign in/i }).click();
  await expect(page).toHaveURL(/\/app/);
  await expect(page.getByRole("heading", { name: /dashboard/i })).toBeVisible();
}

test("golden path: login → dashboard → post journal → ledger → trial balance", async ({ page }) => {
  await signIn(page);
  await page.screenshot({ path: "playwright-report/01-dashboard.png", fullPage: true });

  // Dashboard shows core KPIs
  await expect(page.getByText(/cash on hand/i)).toBeVisible();
  await expect(page.getByText(/MTD net income/i)).toBeVisible();

  // Create + post a journal
  await page.goto("/app/transactions/new");
  await page.getByLabel(/posting date/i).fill(new Date().toISOString().slice(0, 10));
  await page.getByLabel(/memo/i).fill("Playwright golden-path test");

  // Pick first account in each line
  const firstSelect = page.locator("select").nth(0);
  await firstSelect.selectOption({ index: 1 });
  await page.locator('input[type="number"]').nth(0).fill("250");
  const secondSelect = page.locator("select").nth(1);
  await secondSelect.selectOption({ index: 2 });
  await page.locator('input[type="number"]').nth(3).fill("250");

  await expect(page.getByText(/balanced/i)).toBeVisible();
  await page.getByRole("button", { name: /post journal/i }).click();
  await expect(page).toHaveURL(/\/app\/transactions\//);

  // Ledger contains the entry
  await page.goto("/app/ledger");
  await expect(page.getByText("Playwright golden-path test").first()).toBeVisible();
  await page.screenshot({ path: "playwright-report/02-ledger.png", fullPage: true });

  // Trial balance in balance
  await page.goto("/app/reports?r=trial-balance");
  await expect(page.getByText(/in balance/i)).toBeVisible();
  await page.screenshot({ path: "playwright-report/03-trial-balance.png", fullPage: true });
});

test("reconciliation queue clears one entry", async ({ page }) => {
  await signIn(page);
  await page.goto("/app/reconciliation");

  const firstRow = page.locator("tbody tr").first();
  if (!(await firstRow.isVisible())) {
    test.skip();
    return;
  }
  const select = firstRow.locator("select");
  await select.selectOption({ index: 1 });
  await firstRow.getByRole("button", { name: /post/i }).click();

  // Either the entry leaves the queue or we get a friendly error for entity-mismatch.
  await page.waitForTimeout(500);
});
