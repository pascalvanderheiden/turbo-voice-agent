"""Marketing Video REST API routes."""

import asyncio
import logging
import os
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse

from app.models.marketing import MarketingVideo, MarketingVideoCreate

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/marketing", tags=["marketing"])

_marketing_service = None
_marketing_agent = None


def set_marketing_service(service, agent=None) -> None:
    global _marketing_service, _marketing_agent
    _marketing_service = service
    _marketing_agent = agent


def _get_service():
    if _marketing_service is None:
        raise HTTPException(status_code=503, detail="Marketing service unavailable")
    return _marketing_service


@router.get("", response_model=list[MarketingVideo])
async def list_videos(request: Request):
    user_id = getattr(request.state, "user_id", "default-user")
    return await _get_service().with_user(user_id).list()


@router.get("/{video_id}", response_model=MarketingVideo)
async def get_video(video_id: str, request: Request):
    user_id = getattr(request.state, "user_id", "default-user")
    video = await _get_service().with_user(user_id).get_by_id(video_id)
    if video is None:
        raise HTTPException(status_code=404, detail="Video not found")
    return video


@router.post("", response_model=MarketingVideo, status_code=201)
async def create_video(data: MarketingVideoCreate, request: Request):
    user_id = getattr(request.state, "user_id", "default-user")
    video = await _get_service().with_user(user_id).create(data)
    # Auto-trigger the generation pipeline
    if _marketing_agent is not None:
        asyncio.create_task(_marketing_agent.run_pipeline(video.id, user_id=user_id))
        logger.info("Auto-triggered pipeline for new marketing video %s", video.id)
    return video


@router.delete("/{video_id}")
async def delete_video(video_id: str, request: Request):
    user_id = getattr(request.state, "user_id", "default-user")
    ok = await _get_service().with_user(user_id).delete(video_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Video not found")
    return {"success": True}


@router.post("/{video_id}/trigger")
async def trigger_video(video_id: str, request: Request):
    user_id = getattr(request.state, "user_id", "default-user")
    service = _get_service().with_user(user_id)
    video = await service.get_by_id(video_id)
    if video is None:
        raise HTTPException(status_code=404, detail="Video not found")
    if _marketing_agent is None:
        raise HTTPException(status_code=503, detail="Marketing agent unavailable")
    # Reset to pending first so pipeline starts clean
    await service.set_status(video_id, "pending", error=None)
    asyncio.create_task(_marketing_agent.run_pipeline(video_id, user_id=user_id))
    return {"success": True, "message": "Video generation started"}


@router.get("/{video_id}/video")
async def stream_video(video_id: str, request: Request):
    """Stream the generated video file with HTTP Range support for seeking.

    Tries local disk first, then falls back to streaming from Azure Blob Storage.
    """
    user_id = getattr(request.state, "user_id", "default-user")
    service = _get_service().with_user(user_id)
    video = await service.get_by_id(video_id)
    if video is None:
        raise HTTPException(status_code=404, detail="Video not found")

    # Try local file first
    if video.video_path:
        file_path = Path(video.video_path)
        if file_path.exists():
            return _stream_local_file(file_path, request)

    # Fall back to blob storage
    return await _stream_from_blob(video_id, request)

def _stream_local_file(file_path: Path, request: Request) -> StreamingResponse:
    """Stream a video from local disk with Range support."""
    file_size = file_path.stat().st_size
    range_header = request.headers.get("range")

    if range_header:
        range_spec = range_header.replace("bytes=", "")
        parts = range_spec.split("-")
        start = int(parts[0]) if parts[0] else 0
        end = int(parts[1]) if parts[1] else file_size - 1
        end = min(end, file_size - 1)
        content_length = end - start + 1

        async def range_iterator():
            with open(file_path, "rb") as f:
                f.seek(start)
                remaining = content_length
                while remaining > 0:
                    chunk_size = min(8192, remaining)
                    data = f.read(chunk_size)
                    if not data:
                        break
                    remaining -= len(data)
                    yield data

        return StreamingResponse(
            range_iterator(),
            status_code=206,
            media_type="video/mp4",
            headers={
                "Content-Range": f"bytes {start}-{end}/{file_size}",
                "Accept-Ranges": "bytes",
                "Content-Length": str(content_length),
            },
        )

    async def file_iterator():
        with open(file_path, "rb") as f:
            while chunk := f.read(8192):
                yield chunk

    return StreamingResponse(
        file_iterator(),
        media_type="video/mp4",
        headers={
            "Accept-Ranges": "bytes",
            "Content-Length": str(file_size),
        },
    )


async def _stream_from_blob(video_id: str, request: Request) -> StreamingResponse:
    """Stream a video from Azure Blob Storage (marketing-videos container)."""
    storage_account = os.environ.get(
        "AZURE_STORAGE_ACCOUNT_NAME", os.environ.get("AZURE_STORAGE_ACCOUNT", "")
    )
    if not storage_account:
        raise HTTPException(status_code=404, detail="Video file not available")

    try:
        from azure.identity.aio import DefaultAzureCredential
        from azure.storage.blob.aio import BlobServiceClient

        blob_url = f"https://{storage_account}.blob.core.windows.net"
        credential = DefaultAzureCredential()
        try:
            blob_service = BlobServiceClient(account_url=blob_url, credential=credential)
            container_client = blob_service.get_container_client("marketing-videos")
            blob_client = container_client.get_blob_client(f"{video_id}.mp4")

            props = await blob_client.get_blob_properties()
            blob_size = props.size

            range_header = request.headers.get("range")
            if range_header:
                range_spec = range_header.replace("bytes=", "")
                parts = range_spec.split("-")
                start = int(parts[0]) if parts[0] else 0
                end = int(parts[1]) if parts[1] else blob_size - 1
                end = min(end, blob_size - 1)
                content_length = end - start + 1

                stream = await blob_client.download_blob(offset=start, length=content_length)

                async def blob_range_iter():
                    async for chunk in stream.chunks():
                        yield chunk

                return StreamingResponse(
                    blob_range_iter(),
                    status_code=206,
                    media_type="video/mp4",
                    headers={
                        "Content-Range": f"bytes {start}-{end}/{blob_size}",
                        "Accept-Ranges": "bytes",
                        "Content-Length": str(content_length),
                    },
                )

            stream = await blob_client.download_blob()

            async def blob_iter():
                async for chunk in stream.chunks():
                    yield chunk

            return StreamingResponse(
                blob_iter(),
                media_type="video/mp4",
                headers={
                    "Accept-Ranges": "bytes",
                    "Content-Length": str(blob_size),
                },
            )
        finally:
            await credential.close()
            await blob_service.close()
    except Exception:
        logger.exception("Failed to stream video %s from blob storage", video_id)
        raise HTTPException(status_code=404, detail="Video file not available")


@router.get("/by-dev-task/{dev_task_id}", response_model=list[MarketingVideo])
async def list_by_dev_task(dev_task_id: str, request: Request):
    user_id = getattr(request.state, "user_id", "default-user")
    return await _get_service().with_user(user_id).list_by_dev_task(dev_task_id)
