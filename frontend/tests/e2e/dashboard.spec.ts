import { expect, test } from "@playwright/test";

// Live smoke test for the G-STONE ERP Executive redesign (Milestone 1: the
// executive Dashboard; Milestone 2: the Sales/Inventory/Finance nav
// consolidation). Requires a running backend (uvicorn, seeded via
// `python scripts/seed.py`) reachable at the frontend's
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

  // Inventory section (Milestone 2's new control-center KPIs). Scoped to the
  // heading role -- the sidebar's "Inventory" nav link has the same text.
  await expect(page.getByRole("heading", { name: "Inventory", exact: true })).toBeVisible();
  await expect(page.getByText("Available slabs", { exact: true })).toBeVisible();

  // Operational section still present below the executive snapshot.
  await expect(page.getByText("Today", { exact: true })).toBeVisible();

  expect(consoleErrors, `Console errors: ${consoleErrors.join("\n")}`).toEqual([]);
});

test("Sales/Inventory/Finance nav consolidation (Milestone 2)", async ({ page }) => {
  const consoleErrors: string[] = [];
  page.on("console", (msg) => {
    if (msg.type() === "error") consoleErrors.push(msg.text());
  });

  await page.addInitScript(() => window.localStorage.setItem("g_erp_locale", "en"));
  await page.goto("/login");
  await page.getByLabel("Email").fill("owner@g-erp.example");
  await page.getByLabel("Password").fill("ChangeMe123!");
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page.getByText("Choose a company to continue")).toBeVisible();
  await page.getByRole("button", { name: /G-STONE GALLERY/ }).click();
  await expect(page).toHaveURL(/\/dashboard$/);

  const sidebar = page.getByRole("navigation", { name: "Main navigation" });

  // The primary sidebar is now exactly 6 items: Dashboard, Sales, Inventory,
  // Finance, Reports, Settings -- Customers/Projects/Production/Installation/
  // Messages moved out of primary nav (still reachable, just not here).
  await sidebar.getByRole("link", { name: "Sales", exact: true }).click();
  await expect(page).toHaveURL(/\/crm\/customers$/);
  // The merged Sales pipeline tab bar cross-links all five former sections.
  await expect(page.getByRole("link", { name: "Customers", exact: true })).toBeVisible();
  await expect(page.getByRole("link", { name: "Leads", exact: true })).toBeVisible();
  await expect(page.getByRole("link", { name: "Tasks", exact: true })).toBeVisible();
  await expect(page.getByRole("link", { name: "Projects", exact: true })).toBeVisible();
  await expect(page.getByRole("link", { name: "Orders", exact: true })).toBeVisible();

  await sidebar.getByRole("link", { name: "Inventory", exact: true }).click();
  await expect(page).toHaveURL(/\/catalog\/materials$/);

  await sidebar.getByRole("link", { name: "Finance", exact: true }).click();
  await expect(page).toHaveURL(/\/finance\/invoices$/);

  await sidebar.getByRole("link", { name: "Reports", exact: true }).click();
  await expect(page).toHaveURL(/\/reports$/);
  await page.getByRole("link", { name: "Inventory Analytics" }).click();
  await expect(page).toHaveURL(/\/reports\/inventory$/);
  await expect(page.getByText("Available slabs", { exact: true })).toBeVisible();

  expect(consoleErrors, `Console errors: ${consoleErrors.join("\n")}`).toEqual([]);
});
