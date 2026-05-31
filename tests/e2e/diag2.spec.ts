import { test } from "@playwright/test";

test("dashboard deep check via same-origin proxy", async ({ page }) => {
  const reqs: string[] = [];
  page.on("requestfinished", async (r) => {
    if (r.url().includes("/api/")) {
      const resp = await r.response();
      reqs.push(`${r.method()} ${new URL(r.url()).pathname} -> ${resp?.status()}`);
    }
  });
  page.on("requestfailed", (r) => reqs.push(`FAILED ${r.url()} — ${r.failure()?.errorText}`));
  page.on("console", (m) => { if (m.type() === "error") console.log("CONSOLE ERROR:", m.text()); });

  await page.goto("/login");
  await page.getByLabel(/email/i).fill("demo@jrdbooks.io");
  await page.getByLabel(/password/i).fill("demo");
  await page.getByRole("button", { name: /sign in/i }).click();
  await page.waitForTimeout(3000);

  console.log("URL after login:", page.url());
  for (const r of reqs) console.log("  " + r);
  const cash = await page.getByText(/cash on hand/i).count();
  console.log("dashboard 'cash on hand' visible:", cash > 0);
});
