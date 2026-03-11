import { test, expect } from "@playwright/test";

test.describe("Mobile Navigation", () => {
  test("shows bottom tab bar on mobile viewport", async ({ page, isMobile }) => {
    await page.goto("/notes");
    if (isMobile) {
      // Bottom tab bar should be visible
      const tabBar = page.locator("nav").filter({ hasText: "Notes" });
      await expect(tabBar).toBeVisible();
      // Sidebar should NOT be visible
      await expect(page.locator('[data-testid="app-sidebar"]')).not.toBeVisible();
    } else {
      // Sidebar should be visible on desktop
      await expect(page.locator("aside")).toBeVisible();
    }
  });

  test("navigates between tabs on mobile", async ({ page, isMobile }) => {
    test.skip(!isMobile, "Mobile-only test");
    await page.goto("/notes");

    // Tap Ideas tab
    await page.getByRole("link", { name: "Ideas" }).click();
    await expect(page).toHaveURL(/\/ideas/);

    // Tap Research tab
    await page.getByRole("link", { name: "Research" }).click();
    await expect(page).toHaveURL(/\/research/);

    // Tap Specs tab
    await page.getByRole("link", { name: "Specs" }).click();
    await expect(page).toHaveURL(/\/specs/);

    // Tap Voice tab
    await page.getByRole("link", { name: "Voice" }).click();
    await expect(page).toHaveURL(/\/voice/);
  });

  test("shows FAB button on mobile notes page", async ({ page, isMobile }) => {
    test.skip(!isMobile, "Mobile-only test");
    await page.goto("/notes");
    // FAB should be visible
    const fab = page.locator("button").filter({ hasText: "" }).locator("svg");
    await expect(page.locator("button.fixed")).toBeVisible();
  });

  test("opens bottom sheet on mobile for creating note", async ({ page, isMobile }) => {
    test.skip(!isMobile, "Mobile-only test");
    await page.goto("/notes");
    // Click FAB
    await page.locator("button.fixed").click();
    // Bottom sheet should appear
    await expect(page.locator("[class*='bottom-sheet']")).toBeVisible();
  });

  test("shows mobile header with settings on mobile", async ({ page, isMobile }) => {
    test.skip(!isMobile, "Mobile-only test");
    await page.goto("/notes");
    // Mobile header should be visible with settings button
    await expect(page.locator("header")).toBeVisible();
  });
});
