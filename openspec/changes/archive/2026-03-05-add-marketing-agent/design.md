# Design: Add Marketing Agent

## Sora-2 Integration

### API Pattern
The Sora-2 model is deployed as an Azure AI Foundry endpoint in East US 2 (separate region from the main OpenAI resources). The integration follows the same BYOK pattern as the Dev Agent's Codex calls:

```python
# Sora-2 client setup
from openai import AsyncAzureOpenAI

client = AsyncAzureOpenAI(
    azure_endpoint=os.environ["SORA_ENDPOINT"],
    api_key=os.environ["SORA_API_KEY"],
    api_version="2025-04-01-preview",
)

# Video generation call
response = await client.videos.create(
    model=os.environ.get("SORA_DEPLOYMENT", "sora-2"),
    prompt=script_text,
    reference_images=[...],  # Screenshot PNGs from dev task
    duration=180,            # 3 minutes
    resolution="1080p",
)
```

### Input Preparation
- Screenshots are extracted from the dev task's artifacts (type="screenshot")
- Base64 data is decoded to PNG files in a temp directory
- Spec content provides the narrative structure for the script
- The script generator (GPT-5.2) produces a storyboard with timestamps tied to specific screenshots

### Script Generation Prompt Strategy
The script prompt emphasizes **software promotion**:
- Open with the problem the app solves (from spec Overview)
- Walk through key features with matching screenshots
- Highlight the tech stack and design quality (from skill context)
- Close with a call-to-action

## Data Model

```python
class MarketingVideo(BaseModel):
    id: str
    title: str
    dev_task_id: str | None = Field(None, alias="devTaskId")
    spec_id: str | None = Field(None, alias="specId")
    status: str = "pending"  # pending | scripting | generating | completed | failed
    video_path: str | None = Field(None, alias="videoPath")
    script_content: str | None = Field(None, alias="scriptContent")
    duration_seconds: int | None = Field(None, alias="durationSeconds")
    error: str | None = None
    created_at: datetime = Field(alias="createdAt")
    updated_at: datetime = Field(alias="updatedAt")
```

## Video Streaming
The `/api/marketing/{id}/video` endpoint uses `StreamingResponse` with HTTP Range request support for seeking:

```python
@router.get("/{video_id}/video")
async def stream_video(video_id: str, request: Request):
    video = await service.get_by_id(video_id)
    file_path = Path(video.video_path)
    file_size = file_path.stat().st_size
    range_header = request.headers.get("range")
    # ... handle range requests for seeking support
    return StreamingResponse(file_iterator, media_type="video/mp4", headers=headers)
```

## Bidirectional Linking
Same pattern as spec↔devTask:
- `MarketingVideo.devTaskId` → links to the source dev task
- Dev task detail page shows a "Marketing Videos" section with links
- Deleting a dev task optionally cleans up or orphans linked videos
- Deleting a marketing video removes the video file from disk

## Agent Overview Entry
```json
{
    "id": "marketing",
    "name": "Marketing Agent",
    "type": "specialist",
    "model": "sora-2 (Azure AI Foundry, East US 2)",
    "scriptModel": "gpt-5.2",
    "status": "online",
    "tools": ["create_marketing_video", "get_marketing_videos", "get_marketing_video", "delete_marketing_video", "trigger_video_generation"]
}
```
