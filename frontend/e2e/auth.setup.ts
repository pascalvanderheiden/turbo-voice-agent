/**
 * Auth setup for production Playwright tests.
 *
 * Opens a headed browser, navigates to the production site, and waits for
 * the user to complete Entra ID login. Saves the authenticated storage state
 * (sessionStorage + cookies) for use by subsequent test projects.
 *
 * Run:  npx playwright test --config playwright.prod.config.ts --project=auth-setup
 */
import { test as setup, expect } from "@playwright/test";
import path from "path";
import fs from "fs";

const authFile = path.join(__dirname, ".auth/user.json");

setup("authenticate with Entra ID", async ({ page }) => {
  // If we already have a valid auth file from a recent run, skip interactive login
  if (fs.existsSync(authFile)) {
    const stat = fs.statSync(authFile);
    const ageMinutes = (Date.now() - stat.mtimeMs) / 60_000;
    if (ageMinutes < 45) {
      // Token still fresh — reuse
      console.log(`Reusing existing auth state (${Math.round(ageMinutes)}m old)`);
      return;
    }
  }

  console.log("Opening browser for Entra ID login...");
  console.log("Please complete the Microsoft login in the browser window.");

  await page.goto("/");

  // Wait for the Entra login flow to complete and redirect back to the app.
  // After successful login, the app redirects to /dashboard.
  await page.waitForURL("**/dashboard**", { timeout: 120_000 });

  // Verify we're actually authenticated — sidebar or main content should be visible
  await expect(page.locator("body")).not.toContainText("Signing in...", {
    timeout: 15_000,
  });

  console.log("Login successful — saving auth state.");
  await page.context().storageState({ path: authFile });
});
