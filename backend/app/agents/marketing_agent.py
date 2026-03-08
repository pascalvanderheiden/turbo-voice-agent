"""Marketing Agent — generates promotional videos using Sora-2 for apps built by the Dev Agent."""

import asyncio
import base64
import json
import logging
import os
from pathlib import Path

from openai import AsyncAzureOpenAI

from app.models.marketing import MarketingVideo
from app.services.memory_marketing_service import InMemoryMarketingService

logger = logging.getLogger(__name__)

DATA_DIR = Path(os.environ.get("DATA_DIR", "data"))


class MarketingAgent:
    """Agent that generates promotional videos from dev task screenshots + spec content."""

    def __init__(
        self,
        marketing_service: InMemoryMarketingService,
        dev_service=None,
        spec_service=None,
    ):
        self._service = marketing_service
        self._dev_service = dev_service
        self._spec_service = spec_service
        self._openai: AsyncAzureOpenAI | None = None

    def _get_openai(self) -> AsyncAzureOpenAI:
        """Get client for GPT-5.2 (script generation)."""
        if self._openai is None:
            from urllib.parse import urlparse
            from app.agents.config import _get_token_provider

            endpoint = os.environ.get("AZURE_OPENAI_ENDPOINT", "")
            parsed = urlparse(endpoint)
            base_url = f"{parsed.scheme}://{parsed.hostname}"
            token_provider = _get_token_provider()
            if token_provider:
                self._openai = AsyncAzureOpenAI(
                    azure_endpoint=base_url,
                    azure_ad_token_provider=token_provider,
                    api_version="2025-01-01-preview",
                )
            else:
                self._openai = AsyncAzureOpenAI(
                    azure_endpoint=base_url,
                    api_key=os.environ.get("AZURE_OPENAI_API_KEY", ""),
                    api_version="2025-01-01-preview",
                )
        return self._openai

    # ── Tool definitions ──────────────────────────────────────────────

    @property
    def tool_definitions(self) -> list[dict]:
        return [
            {
                "type": "function",
                "function": {
                    "name": "create_marketing_video",
                    "description": "Create a marketing video record linked to a dev task. The video will be generated from the app's screenshots and spec.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "title": {"type": "string", "description": "Title for the marketing video"},
                            "dev_task_id": {"type": "string", "description": "ID of the dev task to promote"},
                        },
                        "required": ["title", "dev_task_id"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "get_marketing_videos",
                    "description": "List all marketing videos.",
                    "parameters": {"type": "object", "properties": {}},
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "get_marketing_video",
                    "description": "Get details of a specific marketing video.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "video_id": {"type": "string", "description": "Marketing video ID"},
                        },
                        "required": ["video_id"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "delete_marketing_video",
                    "description": "Delete a marketing video and its video file.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "video_id": {"type": "string", "description": "Marketing video ID"},
                        },
                        "required": ["video_id"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "trigger_video_generation",
                    "description": "Start the video generation pipeline for a marketing video. Runs in the background — tell the user it's starting.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "video_id": {"type": "string", "description": "Marketing video ID to generate"},
                        },
                        "required": ["video_id"],
                    },
                },
            },
        ]

    # ── Function call handler ─────────────────────────────────────────

    async def handle_function_call(self, function_name: str, arguments: str, user_id: str = "default-user") -> str:
        try:
            args = json.loads(arguments) if arguments else {}
        except json.JSONDecodeError:
            return json.dumps({"error": "Invalid arguments"})

        # Scope services to the authenticated user
        service = self._service.with_user(user_id) if user_id else self._service
        dev_svc = self._dev_service.with_user(user_id) if user_id and self._dev_service and hasattr(self._dev_service, 'with_user') else self._dev_service

        if function_name == "create_marketing_video":
            from app.models.marketing import MarketingVideoCreate
            title = args.get("title", "Promo Video")
            dev_task_id = args.get("dev_task_id")
            if not dev_task_id:
                return json.dumps({"error": "dev_task_id is required"})

            # Verify dev task exists
            if dev_svc:
                task = await dev_svc.get_by_id(dev_task_id)
                if not task:
                    return json.dumps({"error": f"Dev task {dev_task_id} not found"})

            video = await service.create(MarketingVideoCreate(
                title=title, devTaskId=dev_task_id,
            ))

            # Set specId from dev task if available
            if dev_svc:
                task = await dev_svc.get_by_id(dev_task_id)
                if task and task.spec_id:
                    await service.set_status(video.id, "pending", spec_id=task.spec_id)

            return json.dumps({
                "success": True,
                "video": {"id": video.id, "title": video.title, "status": video.status},
            })

        elif function_name == "get_marketing_videos":
            videos = await service.list()
            return json.dumps({
                "videos": [
                    {"id": v.id, "title": v.title, "status": v.status, "devTaskId": v.dev_task_id}
                    for v in videos
                ]
            })

        elif function_name == "get_marketing_video":
            video = await service.get_by_id(args.get("video_id", ""))
            if not video:
                return json.dumps({"error": "Video not found"})
            return json.dumps({
                "video": {
                    "id": video.id, "title": video.title, "status": video.status,
                    "devTaskId": video.dev_task_id, "specId": video.spec_id,
                    "durationSeconds": video.duration_seconds,
                    "hasVideo": video.video_path is not None,
                }
            })

        elif function_name == "delete_marketing_video":
            ok = await service.delete(args.get("video_id", ""))
            return json.dumps({"success": ok})

        elif function_name == "trigger_video_generation":
            video_id = args.get("video_id", "")
            video = await service.get_by_id(video_id)
            if not video:
                return json.dumps({"error": "Video not found"})
            if video.status in ("generating", "scripting", "composing"):
                return json.dumps({"error": "Video generation already in progress"})
            asyncio.create_task(self.run_pipeline(video_id, user_id=user_id))
            return json.dumps({"success": True, "message": "Video generation started"})

        return json.dumps({"error": f"Unknown function: {function_name}"})

    # ── Pipeline ──────────────────────────────────────────────────────

    async def run_pipeline(self, video_id: str, user_id: str = "") -> None:
        """Full pipeline: gather → script → generate → store."""
        # Scope services to the correct user so Cosmos partition keys match
        service = self._service.with_user(user_id) if user_id else self._service
        dev_svc = self._dev_service.with_user(user_id) if user_id and self._dev_service and hasattr(self._dev_service, 'with_user') else self._dev_service
        spec_svc = self._spec_service.with_user(user_id) if user_id and self._spec_service and hasattr(self._spec_service, 'with_user') else self._spec_service
        try:
            # Gather materials
            video = await service.get_by_id(video_id)
            if not video:
                logger.error("Marketing pipeline: video %s not found (user_id=%s)", video_id, user_id)
                return

            screenshots, spec_content = await self._gather_materials_scoped(video, dev_svc, spec_svc)
            if not screenshots:
                await service.set_status(video_id, "failed", error="No screenshots found in linked dev task")
                return

            # Clear previous error on new run
            await service.set_status(video_id, "scripting", error=None)
            script = await self._generate_script(video.title, spec_content, screenshots)
            await service.set_status(video_id, "scripting", script_content=script)

            # Generate video (multi-segment + ffmpeg stitch)
            await service.set_status(video_id, "generating")
            video_path, duration = await self._generate_video(video_id, script, screenshots)

            # Complete
            await service.set_status(
                video_id, "completed",
                video_path=str(video_path),
                duration_seconds=duration,
                script_content=script,
            )
            logger.info("Marketing video %s completed: %s", video_id, video_path)

        except Exception as e:
            logger.exception("Marketing pipeline failed for %s", video_id)
            try:
                await service.set_status(video_id, "failed", error=str(e))
            except Exception:
                logger.exception("Failed to set error status for video %s", video_id)

    async def _gather_materials(self, video: MarketingVideo) -> tuple[list[tuple[str, bytes]], str]:
        """Gather screenshots from dev task and spec content (unscoped)."""
        return await self._gather_materials_scoped(video, self._dev_service, self._spec_service)

    async def _gather_materials_scoped(self, video: MarketingVideo, dev_svc, spec_svc) -> tuple[list[tuple[str, bytes]], str]:
        """Gather screenshots from dev task and spec content using scoped services."""
        screenshots: list[tuple[str, bytes]] = []
        spec_content = ""

        if video.dev_task_id and dev_svc:
            task = await dev_svc.get_by_id(video.dev_task_id)
            if task:
                for artifact in task.artifacts:
                    if artifact.type == "screenshot" and artifact.data:
                        try:
                            img_bytes = base64.b64decode(artifact.data)
                            screenshots.append((artifact.name, img_bytes))
                        except Exception:
                            pass
                # Get spec content if available
                if task.spec_id and spec_svc:
                    spec = await spec_svc.get_by_id(task.spec_id)
                    if spec:
                        spec_content = f"# {spec.title}\n\n{spec.content}"
                        features = await spec_svc.get_features_for_foundation(task.spec_id)
                        for f in features:
                            spec_content += f"\n\n## Feature: {f.title}\n\n{f.content}"
            else:
                logger.warning("Dev task %s not found for video %s", video.dev_task_id, video.id)
        else:
            logger.warning("No dev_task_id or dev_service for video %s", video.id)

        logger.info("Gathered %d screenshots for video %s", len(screenshots), video.id)
        return screenshots, spec_content

    async def _generate_script(self, title: str, spec_content: str, screenshots: list[tuple[str, bytes]]) -> str:
        """Generate a video script with per-segment Sora prompts using GPT-5.2."""
        client = self._get_openai()
        deployment = os.environ.get("AZURE_OPENAI_DEPLOYMENT", "gpt-5.2")

        screenshot_descriptions = "\n".join(
            f"- Screenshot: {name}" for name, _ in screenshots
        )

        response = await client.chat.completions.create(
            model=deployment,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a creative marketing scriptwriter for software products. "
                        "You will create a ~30 second promotional video script broken into "
                        "3 individual segments of ~10 seconds each.\n\n"
                        "Each segment will be generated as a separate Sora-2 video clip, "
                        "then stitched together into one final video.\n\n"
                        "OUTPUT FORMAT — output ONLY a JSON array of 3 segment objects:\n"
                        "```json\n"
                        "[\n"
                        '  {"section": "hook", "narration": "...", "sora_prompt": "..."},\n'
                        '  {"section": "features", "narration": "...", "sora_prompt": "..."},\n'
                        '  {"section": "cta", "narration": "...", "sora_prompt": "..."},\n'
                        "]\n"
                        "```\n\n"
                        "SECTIONS (exactly 3 segments total):\n"
                        "1. HOOK (1 segment) — Grab attention, show the problem, introduce the app\n"
                        "2. FEATURES (1 segment) — Walk through the key features and design\n"
                        "3. CTA (1 segment) — Call to action, closing, logo/tagline\n\n"
                        "SORA PROMPT RULES (critical for quality):\n"
                        "- Follow: [Main subject] + [Scene environment] + [Action] + "
                        "[Camera effects] + [Lighting] + [Style]\n"
                        "- Max 150 words per prompt\n"
                        "- Be highly visual and cinematic\n"
                        "- For software demos: show the app on sleek monitors, floating screens, "
                        "or holographic displays in futuristic settings\n"
                        "- Vary camera angles: orbit, dolly, pan, close-up, wide establishing\n"
                        "- Maintain consistent style: dark theme, neon cyan/pink/purple accents\n"
                        "- Include motion: UI animations, transitions, typing, scrolling\n\n"
                        "Output ONLY the JSON array, no markdown fences, no extra text."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"Create a multi-segment promotional video for: {title}\n\n"
                        f"Available screenshots:\n{screenshot_descriptions}\n\n"
                        f"{'Specification:\n' + spec_content[:3000] if spec_content else 'A modern web application.'}\n"
                    ),
                },
            ],
            max_completion_tokens=2000,
            temperature=0.7,
        )
        return response.choices[0].message.content or ""

    async def _generate_video(self, video_id: str, script: str, screenshots: list[tuple[str, bytes]]) -> tuple[Path, int]:
        """Generate multiple Sora-2 clips and concatenate into a 2-3 min video."""
        import aiohttp
        import subprocess
        import tempfile

        endpoint = os.environ.get("SORA_ENDPOINT", os.environ.get("AZURE_OPENAI_ENDPOINT", "")).rstrip("/")
        api_key = os.environ.get("SORA_API_KEY", os.environ.get("AZURE_OPENAI_API_KEY", ""))
        deployment = os.environ.get("SORA_DEPLOYMENT", "sora-2")

        # Managed identity fallback: get token if no API key set
        if not api_key:
            try:
                from azure.identity.aio import DefaultAzureCredential
                credential = DefaultAzureCredential()
                token = await credential.get_token("https://cognitiveservices.azure.com/.default")
                api_key = token.token
            except Exception as e:
                logger.error("Failed to get managed identity token for Sora-2: %s", e)
                raise

        # Strip project paths for Sora v1 API
        base_endpoint = endpoint
        if base_endpoint.endswith("/openai"):
            base_endpoint = base_endpoint[:-7]
        if "/api/projects/" in base_endpoint:
            base_endpoint = base_endpoint[:base_endpoint.index("/api/projects/")]

        # Prepare output
        output_dir = DATA_DIR / "marketing"
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / f"{video_id}.mp4"
        tmp_dir = Path(tempfile.mkdtemp(prefix=f"turbo-mkt-{video_id[:8]}-"))

        # Parse segment prompts from JSON script
        segments = self._parse_segments(script, screenshots)
        logger.info("Generating %d video segments for %s", len(segments), video_id)

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        create_url = f"{base_endpoint}/openai/v1/videos"

        try:
            clip_paths: list[Path] = []
            async with aiohttp.ClientSession() as session:
                for idx, seg in enumerate(segments):
                    seg_path = tmp_dir / f"seg_{idx:03d}.mp4"
                    prompt = seg["sora_prompt"][:1000]
                    logger.info("Segment %d/%d [%s]: generating...", idx + 1, len(segments), seg.get("section", "?"))

                    # Update progress
                    await self._service.set_status(
                        video_id, "generating",
                        error=None,
                        script_content=f"Generating segment {idx + 1}/{len(segments)}: {seg.get('section', '')}"
                    )

                    payload = {
                        "model": deployment,
                        "prompt": prompt,
                        "size": "1280x720",
                    }

                    # Create video
                    async with session.post(create_url, headers=headers, json=payload) as resp:
                        if resp.status != 200:
                            body = await resp.text()
                            raise RuntimeError(f"Segment {idx} creation failed: {resp.status} - {body}")
                        result = await resp.json()

                    task_id = result.get("id")
                    if not task_id:
                        raise RuntimeError(f"No task ID for segment {idx}: {result}")

                    # Poll for completion
                    retrieve_url = f"{base_endpoint}/openai/v1/videos/{task_id}"
                    for poll in range(60):  # 10 min max per segment
                        await asyncio.sleep(10)
                        async with session.get(retrieve_url, headers=headers) as st_resp:
                            if st_resp.status != 200:
                                body = await st_resp.text()
                                raise RuntimeError(f"Segment {idx} status failed: {st_resp.status} - {body}")
                            st_data = await st_resp.json()

                        status = st_data.get("status")
                        if status == "completed":
                            break
                        if status in ("failed", "cancelled"):
                            logger.warning("Segment %d failed, skipping: %s", idx, st_data.get("error"))
                            break
                    else:
                        logger.warning("Segment %d timed out, skipping", idx)
                        continue

                    if status != "completed":
                        continue

                    # Download clip
                    content_url = f"{base_endpoint}/openai/v1/videos/{task_id}/content"
                    async with session.get(content_url, headers=headers) as dl_resp:
                        if dl_resp.status != 200:
                            logger.warning("Segment %d download failed: %s", idx, dl_resp.status)
                            continue
                        video_data = await dl_resp.read()

                    seg_path.write_bytes(video_data)
                    clip_paths.append(seg_path)
                    logger.info("Segment %d downloaded: %s (%d bytes)", idx, seg_path.name, len(video_data))

            if not clip_paths:
                raise RuntimeError("No video segments were generated successfully")

            # Composing: stitch clips together with ffmpeg
            await self._service.set_status(video_id, "composing", error=None)
            logger.info("Composing %d clips into final video", len(clip_paths))

            # Write ffmpeg concat list
            concat_list = tmp_dir / "concat.txt"
            concat_list.write_text("\n".join(f"file '{p}'" for p in clip_paths))

            proc = subprocess.run(
                ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(concat_list),
                 "-c", "copy", str(output_path)],
                capture_output=True, text=True, timeout=120,
            )
            if proc.returncode != 0:
                # Retry with re-encoding if copy mode fails (different codecs)
                logger.warning("ffmpeg concat copy failed, re-encoding: %s", proc.stderr[-300:])
                proc = subprocess.run(
                    ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(concat_list),
                     "-c:v", "libx264", "-preset", "fast", "-crf", "23",
                     "-c:a", "aac", "-b:a", "128k",
                     "-movflags", "+faststart", str(output_path)],
                    capture_output=True, text=True, timeout=300,
                )
                if proc.returncode != 0:
                    raise RuntimeError(f"ffmpeg failed: {proc.stderr[-500:]}")

            # Calculate actual duration
            duration = len(clip_paths) * 10  # rough estimate
            try:
                probe = subprocess.run(
                    ["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
                     "-of", "csv=p=0", str(output_path)],
                    capture_output=True, text=True, timeout=10,
                )
                if probe.returncode == 0 and probe.stdout.strip():
                    duration = int(float(probe.stdout.strip()))
            except Exception:
                pass

            logger.info("Final video: %s (%d bytes, ~%ds)", output_path, output_path.stat().st_size, duration)
            return output_path, duration

        except Exception as e:
            logger.error("Sora-2 multi-segment generation failed: %s", e)
            raise
        finally:
            import shutil
            shutil.rmtree(tmp_dir, ignore_errors=True)

    def _parse_segments(self, script: str, screenshots: list[tuple[str, bytes]]) -> list[dict]:
        """Parse segment prompts from the GPT-generated JSON script."""
        # Try to parse JSON array from script
        text = script.strip()
        # Strip markdown code fences if present
        if text.startswith("```"):
            text = text.split("\n", 1)[-1]
        if text.endswith("```"):
            text = text.rsplit("```", 1)[0]
        text = text.strip()

        try:
            segments = json.loads(text)
            if isinstance(segments, list) and len(segments) > 0:
                return segments[:3]  # cap at 3 segments (~30 sec)
        except json.JSONDecodeError:
            logger.warning("Failed to parse segment JSON, building fallback prompts")

        # Fallback: generate generic segment prompts
        screenshot_names = [name for name, _ in screenshots[:5]]
        return self._build_fallback_segments(screenshot_names)

    @staticmethod
    def _build_fallback_segments(screenshot_names: list[str]) -> list[dict]:
        """Build fallback segment prompts when GPT JSON parsing fails."""
        screens = ", ".join(screenshot_names) if screenshot_names else "a modern dashboard"
        return [
            {"section": "hook", "sora_prompt": (
                f"A floating holographic display showing {screens} in a futuristic glass office, "
                "app logo materializes with particle effects, camera orbiting slowly around the display, "
                "soft neon cyan and pink accent lighting, cinematic photorealistic style"
            )},
            {"section": "features", "sora_prompt": (
                f"Close-up of a high-resolution monitor displaying {screens}, "
                "cursor clicking through the interface with responsive animations, "
                "shallow depth of field, camera slowly pulling back, "
                "neon purple underglow lighting, crisp tech product demo style"
            )},
            {"section": "cta", "sora_prompt": (
                "Final wide shot of the application on multiple devices, laptop tablet phone, "
                "arranged on a minimalist desk, all screens glowing with the app interface, "
                "camera crane shot rising upward, golden hour lighting mixed with screen glow, "
                "aspirational tech commercial style"
            )},
        ]
