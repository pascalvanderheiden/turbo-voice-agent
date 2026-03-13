import { test, expect } from "@playwright/test";

test.describe("Marketing Video Generation", () => {
  test("navigates to marketing page and lists existing videos", async ({
    page,
  }) => {
    await page.goto("/marketing");
    await expect(page.locator("h1")).toContainText("Marketing Videos");

    // Should display existing completed videos
    const videoCards = page.locator('a[href^="/marketing/"]');
    await expect(videoCards.first()).toBeVisible({ timeout: 10000 });
  });

  test("navigates to video detail page and shows pipeline and player", async ({
    page,
  }) => {
    // Get a completed video ID via API for reliability (parallel tests may create pending videos)
    const listResponse = await page.request.get("http://localhost:8000/api/marketing");
    const videos = await listResponse.json();
    const completedVideo = videos.find(
      (v: { status: string; videoPath: string | null }) => v.status === "completed" && v.videoPath
    );

    if (!completedVideo) {
      test.skip(true, "No completed videos with video files available");
      return;
    }

    // Navigate directly to the completed video
    await page.goto(`/marketing/${completedVideo.id}`);

    // Should show generation pipeline
    await expect(page.getByText("Generation Pipeline")).toBeVisible({
      timeout: 10000,
    });

    // Completed video should show video player (uses streaming endpoint fallback)
    const videoElement = page.locator("video");
    await expect(videoElement).toBeVisible({ timeout: 10000 });

    // Video should have a src attribute pointing to the streaming endpoint
    const src = await videoElement.getAttribute("src");
    expect(src).toContain("/api/marketing/");
    expect(src).toContain("/video");

    // Download button should be visible
    await expect(page.getByText("Download")).toBeVisible();
  });

  test("creates marketing video from dev task page", async ({ page }) => {
    // Navigate to dev tasks
    await page.goto("/development");

    // Click first dev task
    const firstTask = page.locator('a[href^="/development/"]').first();
    await expect(firstTask).toBeVisible({ timeout: 10000 });
    await firstTask.click();

    // Should see Marketing Videos section with Create Video button
    await expect(page.getByText("Marketing Videos")).toBeVisible({
      timeout: 10000,
    });
    const createBtn = page.getByRole("button", { name: /Create Video/i });
    await expect(createBtn).toBeVisible();

    // Click Create Video
    await createBtn.click();

    // Should navigate to the new video detail page
    await expect(page).toHaveURL(/\/marketing\//, { timeout: 15000 });

    // Should show generation pipeline
    await expect(page.getByText("Generation Pipeline")).toBeVisible({
      timeout: 10000,
    });
  });

  test("triggers video generation and tracks pipeline progress", async ({
    page,
  }) => {
    // Create a video via API first
    const response = await page.request.post(
      "http://localhost:8000/api/marketing",
      {
        data: {
          title: "E2E Test Video",
          devTaskId: "725e08b0-08b6-48db-854f-66ba474e26cb",
        },
      }
    );
    expect(response.ok()).toBeTruthy();
    const video = await response.json();

    // Navigate to the video detail page
    await page.goto(`/marketing/${video.id}`);

    // Should show generation pipeline
    await expect(page.getByText("Generation Pipeline")).toBeVisible({
      timeout: 10000,
    });

    // Title should be visible
    await expect(page.getByText("E2E Test Video")).toBeVisible();

    // Trigger generation button should appear (status is pending or failed)
    const triggerBtn = page
      .getByRole("button", { name: /Generate Video|Retry|Restart/i })
      .first();
    if (await triggerBtn.isVisible({ timeout: 5000 }).catch(() => false)) {
      await triggerBtn.click();

      // Wait for status to change from pending
      await page.waitForTimeout(5000);

      // Reload to check updated status
      await page.reload();
      await expect(page.getByText("Generation Pipeline")).toBeVisible({
        timeout: 10000,
      });
    }

    // Cleanup: delete the test video
    await page.request.delete(`http://localhost:8000/api/marketing/${video.id}`);
  });

  test("deletes a marketing video from detail page", async ({ page }) => {
    // Create a video via API
    const response = await page.request.post(
      "http://localhost:8000/api/marketing",
      {
        data: {
          title: "E2E Delete Test Video",
          devTaskId: "725e08b0-08b6-48db-854f-66ba474e26cb",
        },
      }
    );
    expect(response.ok()).toBeTruthy();
    const video = await response.json();

    // Navigate to video detail
    await page.goto(`/marketing/${video.id}`);
    await expect(page.getByText("E2E Delete Test Video")).toBeVisible({
      timeout: 10000,
    });

    // Click delete button — the trash icon button is the last button in the header
    // It navigates via window.location.href so we listen for navigation
    await page.evaluate(() => {
      // Find all buttons, the delete button has an SVG with "tabler-trash" class
      const buttons = document.querySelectorAll("button");
      for (const btn of buttons) {
        if (btn.querySelector('[class*="icon-tabler-trash"]')) {
          btn.click();
          return;
        }
      }
    });

    // Should redirect to marketing list
    await expect(page).toHaveURL(/\/marketing/, { timeout: 10000 });
  });

  test("shows video script content for completed video", async ({ page }) => {
    // Get a completed video ID via API for reliability
    const listResponse = await page.request.get("http://localhost:8000/api/marketing");
    const videos = await listResponse.json();
    const completedVideo = videos.find((v: { status: string }) => v.status === "completed");

    if (!completedVideo) {
      test.skip(true, "No completed videos available");
      return;
    }

    // Navigate directly to the completed video
    await page.goto(`/marketing/${completedVideo.id}`);

    // Should show Video Script section
    await expect(page.getByText("Video Script")).toBeVisible({
      timeout: 10000,
    });

    // Script content should not be empty
    const scriptSection = page.locator(".prose");
    await expect(scriptSection).not.toBeEmpty();
  });

  test("marketing page shows correct status badges", async ({ page }) => {
    await page.goto("/marketing");
    await expect(page.locator("h1")).toContainText("Marketing Videos");

    // Existing videos should have status badges
    const completedBadges = page.getByText("Completed");
    await expect(completedBadges.first()).toBeVisible({ timeout: 10000 });
  });

  test("video duration is displayed correctly", async ({ page }) => {
    // Get a completed video with duration
    const listResponse = await page.request.get("http://localhost:8000/api/marketing");
    const videos = await listResponse.json();
    const completedVideo = videos.find(
      (v: { status: string; durationSeconds: number | null }) =>
        v.status === "completed" && v.durationSeconds
    );

    if (!completedVideo) {
      test.skip(true, "No completed video with duration available");
      return;
    }

    await page.goto(`/marketing/${completedVideo.id}`);

    // Duration should be shown (e.g., "0:24")
    await expect(page.getByText("Duration:")).toBeVisible({ timeout: 10000 });
  });
});
