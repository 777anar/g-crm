import { expect, test } from "@playwright/test";

// Live smoke test for the redesigned executive Dashboard (Milestone 1 of the
// G-STONE ERP Executive redesign). Requires a running backend
// (uvicorn, seeded via `python scripts/seed.py`) reachable at the frontend's
// NEXT_PUBLIC_API_BASE_URL -- this is a real login against a real API, not a
// mocked one, matching this repo's existing "live Playwright smoke test"
// verification convention (see CHANGELOG.md).
test("owner can sign in and see the executive dashboard", async ({ page }) => {
  const consoleErrors: string[] = [];
  page.on("console", (msg) => {
    if (msg.type() === "error") consoleErrors.push(msg.text());
  });

  // The app defaults to Azerbaijani (see lib/i18n/config.ts DEFAULT_LOCALE);
  // pin English via the same localStorage key the language switcher writes
  // so this test's text assertions are deterministic regardless of default.
  await page.addInitScript(() => window.localStorage.setItem("g_erp_locale", "en"));

  await page.goto("/login");
  await page.getByLabel("Email").fill("owner@g-erp.example");
  await page.getByLabel("Password").fill("ChangeMe123!");
  await page.getByRole("button", { name: "Sign in" }).click();

  // Company picker step -- pick G-STONE GALLERY specifically (not `.first()`,
  // since the page's own language-switcher button also renders before this
  // list in the DOM and would otherwise be clicked instead).
  await expect(page.getByText("Choose a company to continue")).toBeVisible();
  await page.getByRole("button", { name: /G-STONE GALLERY/ }).click();

  await expect(page).toHaveURL(/\/dashboard$/);

  // KPI hero row: Revenue / Profit / Active customers / Orders created.
  await expect(page.getByText("Revenue", { exact: true })).toBeVisible();
  await expect(page.getByText("Profit", { exact: true })).toBeVisible();
  await expect(page.getByText("Active customers", { exact: true })).toBeVisible();
  await expect(page.getByText("Orders created", { exact: true })).toBeVisible();

  // Trend + pipeline row.
  await expect(page.getByText("Revenue & profit trend")).toBeVisible();
  await expect(page.getByText("Orders by status")).toBeVisible();

  // Operational section still present below the executive snapshot.
  await expect(page.getByText("Today", { exact: true })).toBeVisible();

  expect(consoleErrors, `Console errors: ${consoleErrors.join("\n")}`).toEqual([]);
});
