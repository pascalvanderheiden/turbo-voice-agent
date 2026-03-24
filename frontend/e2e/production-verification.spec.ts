/**
 * Production verification tests for voice.turboagent.nl
 *
 * Verifies three features:
 * 1. OpenSpec Import — "Import OpenSpec" button on /specs
 * 2. Dev Task Stages — 3 pipeline stages on a dev task detail page
 * 3. Sandbox Stop — Stop/Start buttons on /agents
 *
 * Run:  npx playwright test --config playwright.prod.config.ts --project=production
 */
import { test, expect, Page } from "@playwright/test";

const BACKEND_URL =
  "https://ca-backend-2mta7feoalzyq.icymoss-114d3a42.eastus2.azurecontainerapps.io";

// ── 1. OpenSpec Import ──────────────────────────────────────────────────────

test.describe("OpenSpec Import", () => {
  test("specs page has Import OpenSpec button", async ({ page }) => {
    await page.goto("/specs");
    await page.waitForLoadState("networkidle");

    // The page header should say "Specs"
    await expect(page.locator("h1")).toBeVisible({ timeout: 15_000 });

    // Look for the "Import OpenSpec" button
    const importBtn = page.getByRole("button", { name: /import openspec/i });
    await expect(importBtn).toBeVisible({ timeout: 10_000 });

    // Click it — the import dialog should appear
    await importBtn.click();
    await expect(page.getByText("Import OpenSpec Project")).toBeVisible({
      timeout: 5_000,
    });

    // Dialog should have "Select Folder" button and Cancel/Import buttons
    await expect(page.getByText("Select Folder")).toBeVisible();
    await expect(page.getByRole("button", { name: /cancel/i })).toBeVisible();
    // The dialog has its own "Import" submit button (distinct from the toolbar "Import OpenSpec")
    await expect(
      page.getByRole("button", { name: "Import", exact: true }),
    ).toBeVisible();
  });
});

// ── 2. Dev Task Stages ──────────────────────────────────────────────────────

// Current mockup pipeline: init → implement → screenshots
const EXPECTED_LABELS = ["Init", "Impl", "Screenshots"];

test.describe("Dev Task Stages", () => {
  test("dev task detail page shows all 3 pipeline stages", async ({
    page,
  }) => {
    // Navigate to /development to load the app and get MSAL auth in sessionStorage
    await page.goto("/development");
    await page.waitForLoadState("networkidle");
    await expect(page.locator("h1")).toBeVisible({ timeout: 15_000 });

    // Extract MSAL access token from sessionStorage
    const token = await page.evaluate(() => {
      const keys = Object.keys(sessionStorage);
      const tokenKey = keys.find((k) => k.includes("accesstoken"));
      if (tokenKey) {
        try {
          const data = JSON.parse(sessionStorage.getItem(tokenKey) || "{}");
          return data.secret || null;
        } catch {
          return null;
        }
      }
      return null;
    });

    expect(token, "Could not extract MSAL access token from sessionStorage").toBeTruthy();

    // Create a new dev task via the backend API
    const createResp = await page.request.post(`${BACKEND_URL}/api/dev`, {
      headers: {
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json",
      },
      data: { title: "E2E Pipeline Verification" },
    });

    expect(createResp.ok(), `Failed to create dev task: ${createResp.status()}`).toBe(true);
    const task = await createResp.json();
    const taskId = task.id;
    console.log(`Created task ${taskId} with ${task.stages?.length ?? "?"} stages`);

    try {
      // Navigate to the task detail page
      await page.goto(`/development/${taskId}`);
      await page.waitForLoadState("networkidle");
      await page.waitForTimeout(2_000);

      // Verify pipeline stages are visible
      const foundStages: string[] = [];
      const missingStages: string[] = [];

      for (const label of EXPECTED_LABELS) {
        const loc = page.locator(`text="${label}"`).first();
        const visible = await loc.isVisible({ timeout: 3_000 }).catch(() => false);
        if (visible) {
          foundStages.push(label);
        } else {
          missingStages.push(label);
        }
      }

      console.log(`Found stages: ${foundStages.join(", ")}`);
      if (missingStages.length > 0) {
        console.log(`Missing stages: ${missingStages.join(", ")}`);
      }

      expect(
        foundStages.length,
        `Expected ${EXPECTED_LABELS.length} stages but found ${foundStages.length}. Missing: ${missingStages.join(", ")}`,
      ).toBe(EXPECTED_LABELS.length);
    } finally {
      // Clean up — delete the test task
      const delResp = await page.request.delete(`${BACKEND_URL}/api/dev/${taskId}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      console.log(`Cleanup: deleted task ${taskId} (${delResp.status()})`);
    }
  });
});

// ── 3. Sandbox Stop/Start ───────────────────────────────────────────────────

test.describe("Sandbox Stop/Start", () => {
  test("agents page shows sandbox with Stop or Start button", async ({
    page,
  }) => {
    await page.goto("/agents");
    await page.waitForLoadState("networkidle");

    // Page header should say "Agents"
    await expect(page.locator("h1")).toBeVisible({ timeout: 15_000 });

    // Look for the "Sandbox" section heading
    const sandboxHeading = page.getByText("Sandbox", { exact: true });
    await expect(sandboxHeading.first()).toBeVisible({ timeout: 10_000 });

    // Either Stop or Start button should be visible depending on sandbox state
    const stopBtn = page.getByRole("button", { name: /^stop$/i });
    const startBtn = page.getByRole("button", { name: /^start$/i });

    const stopVisible = await stopBtn.isVisible().catch(() => false);
    const startVisible = await startBtn.isVisible().catch(() => false);

    console.log(`Sandbox buttons — Stop: ${stopVisible}, Start: ${startVisible}`);

    expect(
      stopVisible || startVisible,
      "Expected either Stop or Start button to be visible on the Agents page",
    ).toBe(true);

    // Verify Recreate button is also present (always visible)
    const recreateBtn = page.getByRole("button", { name: /recreate/i });
    await expect(recreateBtn).toBeVisible({ timeout: 5_000 });

    // Verify sandbox status indicator is present
    const statusTexts = ["Running", "Busy", "Stopped", "Provisioning", "Error", "Not Configured"];
    let sandboxStatus = "unknown";
    for (const status of statusTexts) {
      const el = page.getByText(status, { exact: false });
      if (await el.first().isVisible().catch(() => false)) {
        sandboxStatus = status;
        break;
      }
    }
    console.log(`Sandbox status: ${sandboxStatus}`);
  });
});
