import { test } from "@playwright/test";

const PAGES = [
  "/",
  "/login",
  "/app",
  "/app/banking",
  "/app/reconciliation",
  "/app/transactions",
  "/app/ledger",
  "/app/reports",
  "/app/invoices",
  "/app/bills",
  "/app/customers",
  "/app/vendors",
  "/app/inventory",
  "/app/fuel",
  "/app/repair-orders",
  "/app/payroll",
  "/app/ai",
  "/app/integrations",
  "/app/audit",
  "/app/settings",
];

test("diagnostic: capture console + network errors on every page", async ({ page }) => {
  // Log in first so /app pages render.
  await page.goto("/login");
  await page.getByLabel(/email/i).fill("demo@jrdbooks.io");
  await page.getByLabel(/password/i).fill("demo");
  await page.getByRole("button", { name: /sign in/i }).click();
  await page.waitForTimeout(1500);

  for (const path of PAGES) {
    const consoleErrors: string[] = [];
    const failedRequests: string[] = [];
    const onConsole = (msg: import("@playwright/test").ConsoleMessage) => {
      if (msg.type() === "error") consoleErrors.push(msg.text());
    };
    const onFailed = (req: import("@playwright/test").Request) => {
      failedRequests.push(`${req.method()} ${req.url()} — ${req.failure()?.errorText ?? "?"}`);
    };
    page.on("console", onConsole);
    page.on("requestfailed", onFailed);

    let navError = "";
    try {
      await page.goto(path, { waitUntil: "networkidle", timeout: 10000 });
    } catch (e) {
      navError = String(e);
    }
    await page.waitForTimeout(800);

    page.off("console", onConsole);
    page.off("requestfailed", onFailed);

    const heading = await page.locator("h1").first().textContent().catch(() => null);
    // eslint-disable-next-line no-console
    console.log(
      `\n=== ${path} ===\n` +
        `  url: ${page.url()}\n` +
        `  h1: ${heading ?? "(none)"}\n` +
        `  navError: ${navError || "none"}\n` +
        `  consoleErrors(${consoleErrors.length}): ${consoleErrors.slice(0, 3).join(" | ") || "none"}\n` +
        `  failedRequests(${failedRequests.length}): ${failedRequests.slice(0, 3).join(" | ") || "none"}`
    );
  }
});
