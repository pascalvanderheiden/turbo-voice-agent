/**
 * End-to-end test for Dev-Task pipelines.
 *
 * Verifies:
 * 1. Create a mockup dev-task via API
 * 2. Detail page shows correct 3 pipeline stages (Init, Implement, Screenshots)
 * 3. StatusPanel renders (terminal/sandbox section present)
 * 4. Mode badge shows "Mockup" for mockup tasks
 * 5. Slides mode task shows 2 stages (Init, Slides)
 * 6. Archive filter tabs work on development list page
 * 7. Archive/unarchive round-trip works
 *
 * Run:  npx playwright test e2e/dev-task-e2e.spec.ts --project="Desktop Chrome"
 */
import { test, expect } from "@playwright/test";

const BACKEND_URL =
  process.env.BACKEND_URL ||
  "https://ca-backend-2mta7feoalzyq.icymoss-114d3a42.eastus2.azurecontainerapps.io";

/** Extract MSAL access token from sessionStorage. */
async function getToken(page: import("@playwright/test").Page): Promise<string> {
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
  expect(token, "Could not extract MSAL access token").toBeTruthy();
  return token as string;
}

// ── Helpers ────────────────────────────────────────────────────────────────

async function createTask(
  page: import("@playwright/test").Page,
  token: string,
  body: Record<string, unknown>,
) {
  const resp = await page.request.post(`${BACKEND_URL}/api/dev`, {
    headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
    data: body,
  });
  expect(resp.ok(), `Create task failed: ${resp.status()}`).toBe(true);
  return resp.json();
}

async function deleteTask(
  page: import("@playwright/test").Page,
  token: string,
  taskId: string,
) {
  await page.request.delete(`${BACKEND_URL}/api/dev/${taskId}`, {
    headers: { Authorization: `Bearer ${token}` },
  });
}

/** Count visible stage nodes on the detail page by checking the SHORT_LABELS text. */
async function countVisibleStages(
  page: import("@playwright/test").Page,
  stageLabels: string[],
): Promise<string[]> {
  const found: string[] = [];
  for (const label of stageLabels) {
    // StageNode renders labels in a small text span under the icon
    const loc = page.locator(`text="${label}"`).first();
    if (await loc.isVisible({ timeout: 3_000 }).catch(() => false)) {
      found.push(label);
    }
  }
  return found;
}

// ── 1. Mockup Dev-Task Detail ──────────────────────────────────────────────

// Current mockup pipeline: init → skills → implement → screenshots
const MOCKUP_LABELS = ["Init", "Skills", "Impl", "Screenshots"];

test.describe("Mockup Dev-Task Pipeline", () => {
  let token: string;
  let taskId: string;

  test.beforeAll(async ({ browser }) => {
    const ctx = await browser.newContext();
    const page = await ctx.newPage();
    await page.goto("/development");
    await page.waitForLoadState("networkidle");
    await expect(page.locator("h1")).toBeVisible({ timeout: 15_000 });
    token = await getToken(page);
    const task = await createTask(page, token, { title: "E2E Mockup Test" });
    taskId = task.id;
    await ctx.close();
  });

  test.afterAll(async ({ browser }) => {
    const ctx = await browser.newContext();
    const page = await ctx.newPage();
    await page.goto("/development");
    await page.waitForLoadState("networkidle");
    const t = await getToken(page);
    await deleteTask(page, t, taskId);
    await ctx.close();
  });

  test("detail page shows 4 mockup pipeline stages", async ({ page }) => {
    await page.goto(`/development/${taskId}`);
    await page.waitForLoadState("networkidle");
    await page.waitForTimeout(2_000);

    const found = await countVisibleStages(page, MOCKUP_LABELS);
    expect(
      found.length,
      `Found ${found.join(",")} — expected all ${MOCKUP_LABELS.length}`,
    ).toBe(MOCKUP_LABELS.length);
  });

  test("mode badge shows Mockup", async ({ page }) => {
    await page.goto(`/development/${taskId}`);
    await page.waitForLoadState("networkidle");
    await expect(page.getByText("Mockup")).toBeVisible({ timeout: 10_000 });
  });

  test("sandbox terminal section is present", async ({ page }) => {
    await page.goto(`/development/${taskId}`);
    await page.waitForLoadState("networkidle");
    const terminal = page.getByText("Copilot CLI Sandbox");
    const screenshots = page.getByText("No preview screenshots yet");
    const hasTerminal = await terminal.isVisible({ timeout: 5_000 }).catch(() => false);
    const hasScreenshots = await screenshots.isVisible({ timeout: 3_000 }).catch(() => false);
    expect(hasTerminal || hasScreenshots).toBe(true);
  });

  test("screenshots section shows empty state", async ({ page }) => {
    await page.goto(`/development/${taskId}`);
    await page.waitForLoadState("networkidle");
    await expect(page.getByText("No preview screenshots yet")).toBeVisible({ timeout: 10_000 });
  });
});

// ── 2. Slides Dev-Task Stages ──────────────────────────────────────────────

// Current slides pipeline: init → skills → slides
const SLIDES_LABELS = ["Init", "Skills", "Slides"];

test.describe("Slides Dev-Task Pipeline", () => {
  let token: string;
  let taskId: string;

  test.beforeAll(async ({ browser }) => {
    const ctx = await browser.newContext();
    const page = await ctx.newPage();
    await page.goto("/development");
    await page.waitForLoadState("networkidle");
    await expect(page.locator("h1")).toBeVisible({ timeout: 15_000 });
    token = await getToken(page);
    const task = await createTask(page, token, { title: "E2E Slides Test", mode: "slides" });
    taskId = task.id;
    await ctx.close();
  });

  test.afterAll(async ({ browser }) => {
    const ctx = await browser.newContext();
    const page = await ctx.newPage();
    await page.goto("/development");
    await page.waitForLoadState("networkidle");
    const t = await getToken(page);
    await deleteTask(page, t, taskId);
    await ctx.close();
  });

  test("detail page shows 3 slides pipeline stages", async ({ page }) => {
    await page.goto(`/development/${taskId}`);
    await page.waitForLoadState("networkidle");
    await page.waitForTimeout(2_000);

    const found = await countVisibleStages(page, SLIDES_LABELS);
    expect(
      found.length,
      `Found ${found.join(",")} — expected ${SLIDES_LABELS.length} slides stages`,
    ).toBe(SLIDES_LABELS.length);
  });

  test("mode badge shows Slidedeck", async ({ page }) => {
    await page.goto(`/development/${taskId}`);
    await page.waitForLoadState("networkidle");
    await expect(page.getByText("Slidedeck")).toBeVisible({ timeout: 10_000 });
  });
});

// ── 3. Archive Filter ──────────────────────────────────────────────────────

test.describe("Dev-Task Archive Flow", () => {
  let token: string;
  let taskId: string;

  test.beforeAll(async ({ browser }) => {
    const ctx = await browser.newContext();
    const page = await ctx.newPage();
    await page.goto("/development");
    await page.waitForLoadState("networkidle");
    await expect(page.locator("h1")).toBeVisible({ timeout: 15_000 });
    token = await getToken(page);
    const task = await createTask(page, token, { title: "E2E Archive Test" });
    taskId = task.id;
    await ctx.close();
  });

  test.afterAll(async ({ browser }) => {
    const ctx = await browser.newContext();
    const page = await ctx.newPage();
    await page.goto("/development");
    await page.waitForLoadState("networkidle");
    const t = await getToken(page);
    // Unarchive first in case it was archived
    await page.request.patch(`${BACKEND_URL}/api/dev/${taskId}/unarchive`, {
      headers: { Authorization: `Bearer ${t}` },
    });
    await deleteTask(page, t, taskId);
    await ctx.close();
  });

  test("archive filter tabs are visible", async ({ page }) => {
    await page.goto("/development");
    await page.waitForLoadState("networkidle");
    await expect(page.getByRole("button", { name: "Active" })).toBeVisible({ timeout: 10_000 });
    await expect(page.getByRole("button", { name: "Archived" })).toBeVisible();
    await expect(page.getByRole("button", { name: "All" })).toBeVisible();
  });

  test("task visible in Active, hidden after archive, visible in Archived", async ({ page }) => {
    await page.goto("/development");
    await page.waitForLoadState("networkidle");

    // Task should be visible in Active (default) view
    await expect(page.getByText("E2E Archive Test")).toBeVisible({ timeout: 10_000 });

    // Archive the task via API
    const archiveResp = await page.request.patch(`${BACKEND_URL}/api/dev/${taskId}/archive`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    expect(archiveResp.ok()).toBe(true);

    // Refresh Active — task should be gone
    await page.getByRole("button", { name: "Active" }).click();
    await page.waitForTimeout(1_500);
    const visibleInActive = await page.getByText("E2E Archive Test").isVisible().catch(() => false);
    expect(visibleInActive).toBe(false);

    // Switch to Archived — task should appear
    await page.getByRole("button", { name: "Archived" }).click();
    await page.waitForTimeout(1_500);
    await expect(page.getByText("E2E Archive Test")).toBeVisible({ timeout: 10_000 });

    // Switch to All — task should appear
    await page.getByRole("button", { name: "All" }).click();
    await page.waitForTimeout(1_500);
    await expect(page.getByText("E2E Archive Test")).toBeVisible({ timeout: 10_000 });

    // Unarchive via API
    await page.request.patch(`${BACKEND_URL}/api/dev/${taskId}/unarchive`, {
      headers: { Authorization: `Bearer ${token}` },
    });
  });
});

// ── 4. StatusPanel Rendering ───────────────────────────────────────────────

test.describe("StatusPanel Rendering", () => {
  test("development detail page renders without errors", async ({ page }) => {
    await page.goto("/development");
    await page.waitForLoadState("networkidle");
    await expect(page.locator("h1")).toBeVisible({ timeout: 15_000 });

    // Check console for React errors
    const errors: string[] = [];
    page.on("pageerror", (err) => errors.push(err.message));

    const token = await getToken(page);
    const task = await createTask(page, token, { title: "E2E Status Panel Test" });

    try {
      await page.goto(`/development/${task.id}`);
      await page.waitForLoadState("networkidle");
      await page.waitForTimeout(2_000);

      // Page should render without critical errors
      const criticalErrors = errors.filter(
        (e) => e.includes("Cannot read") || e.includes("is not a function") || e.includes("undefined"),
      );
      expect(criticalErrors, `Page errors: ${criticalErrors.join("; ")}`).toHaveLength(0);

      // The title should be visible
      await expect(page.getByText("E2E Status Panel Test")).toBeVisible({ timeout: 5_000 });
    } finally {
      await deleteTask(page, token, task.id);
    }
  });
});
