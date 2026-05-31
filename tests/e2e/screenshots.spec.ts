import { expect, test } from "@playwright/test";

test.use({ viewport: { width: 1440, height: 900 } });

async function login(page: import("@playwright/test").Page) {
  await page.goto("/login");
  await page.getByLabel(/email/i).fill("demo@jrdbooks.io");
  await page.getByLabel(/password/i).fill("demo");
  await page.getByRole("button", { name: /sign in/i }).click();
  await expect(page).toHaveURL(/\/app/);
}

test("01 - marketing landing", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByText(/the accounting platform/i)).toBeVisible();
  await page.screenshot({ path: "/tmp/shots/01-landing.png", fullPage: true });
});

test("02 - login", async ({ page }) => {
  await page.goto("/login");
  await expect(page.getByText(/sign in to jrdbooks/i)).toBeVisible();
  await page.screenshot({ path: "/tmp/shots/02-login.png", fullPage: true });
});

test("03 - dashboard", async ({ page }) => {
  await login(page);
  await page.waitForLoadState("networkidle");
  await page.screenshot({ path: "/tmp/shots/03-dashboard.png", fullPage: true });
});

test("04 - ledger", async ({ page }) => {
  await login(page);
  await page.goto("/app/ledger");
  await page.waitForLoadState("networkidle");
  await page.screenshot({ path: "/tmp/shots/04-ledger.png", fullPage: true });
});

test("05 - new journal", async ({ page }) => {
  await login(page);
  await page.goto("/app/transactions/new");
  await page.waitForLoadState("networkidle");
  await page.screenshot({ path: "/tmp/shots/05-new-journal.png", fullPage: true });
});

test("06 - reports trial balance", async ({ page }) => {
  await login(page);
  await page.goto("/app/reports?r=trial-balance");
  await page.waitForLoadState("networkidle");
  await page.screenshot({ path: "/tmp/shots/06-trial-balance.png", fullPage: true });
});

test("07 - reports p&l", async ({ page }) => {
  await login(page);
  await page.goto("/app/reports?r=pnl");
  await page.waitForLoadState("networkidle");
  await page.screenshot({ path: "/tmp/shots/07-pnl.png", fullPage: true });
});

test("08 - banking", async ({ page }) => {
  await login(page);
  await page.goto("/app/banking");
  await page.waitForLoadState("networkidle");
  await page.screenshot({ path: "/tmp/shots/08-banking.png", fullPage: true });
});

test("09 - reconciliation queue", async ({ page }) => {
  await login(page);
  await page.goto("/app/reconciliation");
  await page.waitForLoadState("networkidle");
  await page.screenshot({ path: "/tmp/shots/09-reconciliation.png", fullPage: true });
});

test("10 - integrations", async ({ page }) => {
  await login(page);
  await page.goto("/app/integrations");
  await page.waitForLoadState("networkidle");
  await page.screenshot({ path: "/tmp/shots/10-integrations.png", fullPage: true });
});
