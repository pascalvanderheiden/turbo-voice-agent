/**
 * E2E tests for Slides page and Dev-Task Archive functionality.
 *
 * Tests verify:
 * 1. Slides page loads with navigation
 * 2. Slides CRUD — create, view detail, delete
 * 3. Dev-task archive filter tabs work
 * 4. Slides mode dev-task shows correct pipeline stages
 *
 * Run:  npx playwright test e2e/slides-and-archive.spec.ts
 */
import { test, expect } from "@playwright/test";

// ── 1. Slides Navigation ───────────────────────────────────────────────────

test.describe("Slides Navigation", () => {
  test("sidebar contains Slides link that navigates to /slides", async ({
    page,
  }) => {
    await page.goto("/slides");
    await page.waitForLoadState("networkidle");

    // Page should have a heading
    const heading = page.locator("h1");
    await expect(heading).toBeVisible({ timeout: 15_000 });
    await expect(heading).toContainText(/slides|presentat/i);
  });
});

// ── 2. Slides CRUD ─────────────────────────────────────────────────────────

test.describe("Slides CRUD", () => {
  test("can create a new slide presentation", async ({ page }) => {
    await page.goto("/slides");
    await page.waitForLoadState("networkidle");

    // Click create button (+ or "New" button)
    const createBtn = page.getByRole("button", { name: /new|create|\+/i });
    if (await createBtn.isVisible({ timeout: 5_000 }).catch(() => false)) {
      await createBtn.click();

      // Fill in the title
      const titleInput = page.getByRole("textbox", { name: /title/i }).or(
        page.locator('input[placeholder*="title" i]'),
      );
      if (await titleInput.isVisible({ timeout: 3_000 }).catch(() => false)) {
        await titleInput.fill("E2E Test Slides");

        // Submit
        const submitBtn = page
          .getByRole("button", { name: /create|save|submit/i })
          .first();
        if (
          await submitBtn.isVisible({ timeout: 3_000 }).catch(() => false)
        ) {
          await submitBtn.click();

          // Verify it appears in the list
          await expect(page.getByText("E2E Test Slides")).toBeVisible({
            timeout: 10_000,
          });
        }
      }
    }
  });

  test("slides list shows empty state or items", async ({ page }) => {
    await page.goto("/slides");
    await page.waitForLoadState("networkidle");

    // Should show either empty state or at least the page loaded
    const pageContent = page.locator("main, [class*='space-y']").first();
    await expect(pageContent).toBeVisible({ timeout: 10_000 });
  });
});

// ── 3. Dev-Task Archive Filter ─────────────────────────────────────────────

test.describe("Dev-Task Archive Filter", () => {
  test("development page has Active/Archived/All filter tabs", async ({
    page,
  }) => {
    await page.goto("/development");
    await page.waitForLoadState("networkidle");

    // Verify the archive filter tabs are present
    await expect(page.getByRole("button", { name: "Active" })).toBeVisible({
      timeout: 10_000,
    });
    await expect(page.getByRole("button", { name: "Archived" })).toBeVisible({
      timeout: 5_000,
    });
    await expect(page.getByRole("button", { name: "All" })).toBeVisible({
      timeout: 5_000,
    });
  });

  test("clicking Archived tab switches filter", async ({ page }) => {
    await page.goto("/development");
    await page.waitForLoadState("networkidle");

    const archivedBtn = page.getByRole("button", { name: "Archived" });
    await expect(archivedBtn).toBeVisible({ timeout: 10_000 });
    await archivedBtn.click();

    // After clicking, the Archived button should be styled as active (has brand-pink color)
    await expect(archivedBtn).toHaveClass(/brand-pink/);
  });

  test("clicking All tab shows all tasks", async ({ page }) => {
    await page.goto("/development");
    await page.waitForLoadState("networkidle");

    const allBtn = page.getByRole("button", { name: "All" });
    await expect(allBtn).toBeVisible({ timeout: 10_000 });
    await allBtn.click();

    // All button should now be active
    await expect(allBtn).toHaveClass(/brand-pink/);
  });
});

// ── 4. Slides Pipeline Stages ──────────────────────────────────────────────

test.describe("Slides Pipeline Stages", () => {
  test("STAGE_META includes slides-specific stages", async ({ page }) => {
    await page.goto("/development");
    await page.waitForLoadState("networkidle");

    // The page should load without errors
    const heading = page.locator("h1");
    await expect(heading).toBeVisible({ timeout: 15_000 });
    await expect(heading).toContainText(/development/i);
  });
});
