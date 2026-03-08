"""Voice WebSocket endpoint — proxies audio between client and Azure Voice Live.

Uses the OpenAI Realtime API over WebSocket to proxy audio to/from the voice model.
The client sends PCM16 audio as base64, and receives response audio and events.
Long-running tasks (research, spec generation, idea refinement) run in the background
and inject completion messages into the voice session when done.
"""

import asyncio
import base64
import json
import logging
import os

import websockets
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.agents.supervisor import SupervisorAgent
from app.auth import validate_token
from app.voice.function_handler import handle_voice_function_call
from app.voice.session import build_session_tools, get_voice_config
from app.voice.background_tasks import BackgroundTaskManager

logger = logging.getLogger(__name__)
router = APIRouter()

_supervisor: SupervisorAgent | None = None

# Functions that should run in the background during voice sessions
BACKGROUND_FUNCTIONS = {
    "web_search", "deep_research", "refine_idea",
    "generate_spec", "optimize_spec",
    "trigger_video_generation",
}


def set_supervisor(supervisor: SupervisorAgent) -> None:
    global _supervisor
    _supervisor = supervisor


def _build_realtime_ws_url(config: dict) -> str:
    """Build the OpenAI Realtime API WebSocket URL from config.
    
    The Foundry endpoint may include a project path like /api/projects/xxx.
    The Realtime API only needs the host: wss://<host>/openai/realtime?...
    """
    from urllib.parse import urlparse
    
    parsed = urlparse(config["endpoint"])
    host = parsed.hostname
    deployment = config["deployment"]
    return f"wss://{host}/openai/realtime?api-version=2025-04-01-preview&deployment={deployment}"


@router.websocket("/ws/voice")
async def voice_websocket(ws: WebSocket):
    """WebSocket endpoint that proxies audio to/from Azure Voice Live."""
    await ws.accept()

    # Authenticate WebSocket connection via token query parameter
    user_id = "default-user"
    if os.environ.get("AUTH_DISABLED", "").lower() == "true":
        user_id = "00000000-0000-0000-0000-000000000000"
    else:
        token = ws.query_params.get("token", "")
        if token:
            try:
                claims = await validate_token(token)
                user_id = claims["oid"]
            except (ValueError, Exception) as e:
                logger.warning("WebSocket auth failed: %s", e)
                await ws.close(code=4001, reason="Authentication failed")
                return
        elif os.environ.get("ENTRA_TENANT_ID"):
            # Auth is configured but no token provided
            await ws.close(code=4001, reason="Missing authentication token")
            return

    if _supervisor is None:
        await ws.close(code=1011, reason="Supervisor agent not initialized")
        return

    # Read language from query string
    lang = ws.query_params.get("lang", "en")
    if lang not in ("en", "nl"):
        lang = "en"

    config = get_voice_config(lang=lang)
    rt_url = _build_realtime_ws_url(config)
    tools = build_session_tools(_supervisor.tool_definitions)
    logger.info("Voice session config: url=%s, voice=%s, lang=%s, tools=%d", rt_url, config["voice"], lang, len(tools))
    logger.info("Tools: %s", [t.get("name") for t in tools if t.get("type") == "function"])

    # Build auth headers: managed identity token or API key
    auth_headers = {}
    if config["api_key"]:
        auth_headers["api-key"] = config["api_key"]
    else:
        try:
            from azure.identity.aio import DefaultAzureCredential
            credential = DefaultAzureCredential()
            token = await credential.get_token("https://cognitiveservices.azure.com/.default")
            auth_headers["Authorization"] = f"Bearer {token.token}"
        except Exception as e:
            logger.error("Failed to get managed identity token for Voice Live: %s", e)
            await ws.close(code=1011, reason="Authentication failed")
            return

    try:
        async with websockets.connect(
            rt_url,
            additional_headers=auth_headers,
        ) as rt_ws:
            # Configure the session — relaxed VAD for background noise tolerance
            session_update = {
                "type": "session.update",
                "session": {
                    "voice": config["voice"],
                    "instructions": config["instructions"],
                    "input_audio_format": "pcm16",
                    "output_audio_format": "pcm16",
                    "input_audio_transcription": {"model": "gpt-4o-transcribe"},
                    "turn_detection": {
                        "type": "server_vad",
                        "threshold": 0.6,
                        "prefix_padding_ms": 300,
                        "silence_duration_ms": 700,
                    },
                    "tools": tools,
                },
            }
            await rt_ws.send(json.dumps(session_update))

            # Wait for session.created and session.updated
            init_msg = json.loads(await rt_ws.recv())
            logger.info("Realtime init: %s", init_msg.get("type"))

            if init_msg.get("type") == "session.created":
                update_msg = json.loads(await rt_ws.recv())
                logger.info("Realtime update: %s", update_msg.get("type"))
                if update_msg.get("type") == "error":
                    error_detail = update_msg.get("error", {})
                    error_msg = error_detail.get("message", "Session config failed")
                    logger.error("Realtime session.update error: %s", error_detail)
                    await ws.send_json({"type": "error", "message": error_msg})
                    return

            # Notify client that session is ready
            await ws.send_json({"type": "session.ready"})

            # Send greeting — make the agent speak first
            greeting_event = {
                "type": "response.create",
                "response": {
                    "instructions": config["greeting"],
                },
            }
            await rt_ws.send(json.dumps(greeting_event))

            async def receive_from_client():
                """Receive audio from client and forward to Realtime API."""
                try:
                    while True:
                        data = await ws.receive_text()
                        msg = json.loads(data)
                        if msg.get("type") == "input_audio":
                            event = {
                                "type": "input_audio_buffer.append",
                                "audio": msg["audio"],  # Already base64
                            }
                            await rt_ws.send(json.dumps(event))
                        elif msg.get("type") == "input_audio_buffer.commit":
                            await rt_ws.send(
                                json.dumps({"type": "input_audio_buffer.commit"})
                            )
                except WebSocketDisconnect:
                    logger.info("Client disconnected")
                except Exception:
                    logger.exception("Error receiving from client")

            response_active = False
            task_mgr = BackgroundTaskManager()

            async def _run_background_task(
                task_mgr: BackgroundTaskManager,
                supervisor: SupervisorAgent,
                fn_name: str,
                call_id: str,
                arguments: str,
                task_id: str,
            ):
                """Run a slow function call in the background."""
                try:
                    result = await handle_voice_function_call(
                        supervisor, fn_name, call_id, arguments
                    )
                    output = result.get("output", "")
                    agent = result.get("agent", "Agent")
                    try:
                        data = json.loads(output)
                        if data.get("success"):
                            summary = f"{agent} completed {fn_name} successfully."
                            if "specs" in data:
                                summary = f"Generated {len(data['specs'])} specs."
                            elif "idea" in data:
                                title = data['idea'].get('title', '')
                                summary = f"Idea '{title}' has been refined."
                            elif "spec" in data:
                                title = data['spec'].get('title', '')
                                summary = f"Spec '{title}' has been optimized."
                        elif data.get("status") == "started":
                            # Research returns "started" — wait for actual completion
                            summary = data.get("message", "Task started.")
                        else:
                            summary = data.get("error", "Task completed.")
                    except (json.JSONDecodeError, KeyError):
                        summary = "Task completed."
                    await task_mgr.complete_task(task_id, summary)
                except Exception as e:
                    logger.exception("Background task %s failed", fn_name)
                    await task_mgr.fail_task(task_id, str(e))

            async def poll_background_completions():
                """Poll for completed background tasks and inject messages into voice session."""
                try:
                    while True:
                        completed = await task_mgr.get_completion()
                        if completed:
                            await ws.send_json({
                                "type": "agent.activity",
                                "action": completed.action,
                                "status": completed.status,
                                "output": completed.result_summary,
                            })

                            status_text = "completed" if completed.status == "completed" else "failed"
                            inject_msg = (
                                f"[BACKGROUND TASK UPDATE] The {completed.action} task has {status_text}. "
                                f"Details: {completed.result_summary} "
                                f"Please proactively inform the user about this and ask if they'd like to "
                                f"hear the results or take any follow-up action."
                            )
                            await rt_ws.send(json.dumps({
                                "type": "conversation.item.create",
                                "item": {
                                    "type": "message",
                                    "role": "user",
                                    "content": [{"type": "input_text", "text": inject_msg}],
                                },
                            }))
                            await rt_ws.send(json.dumps({"type": "response.create"}))
                            logger.info("Injected background completion for %s", completed.action)

                        await asyncio.sleep(1.5)
                except asyncio.CancelledError:
                    pass
                except Exception:
                    logger.exception("Background poll error")

            async def receive_from_realtime():
                """Receive events from Realtime API and forward to client."""
                nonlocal response_active
                try:
                    async for raw_msg in rt_ws:
                        event = json.loads(raw_msg)
                        event_type = event.get("type", "")

                        if event_type == "response.audio.delta":
                            response_active = True
                            await ws.send_json(
                                {
                                    "type": "response.audio.delta",
                                    "audio": event.get("delta", ""),
                                }
                            )

                        elif event_type == "response.audio_transcript.delta":
                            await ws.send_json(
                                {
                                    "type": "response.audio_transcript.delta",
                                    "transcript": event.get("delta", ""),
                                }
                            )

                        elif event_type == "response.audio_transcript.done":
                            await ws.send_json(
                                {
                                    "type": "response.audio_transcript.done",
                                    "transcript": event.get("transcript", ""),
                                }
                            )

                        elif event_type == "input_audio_buffer.speech_started":
                            await ws.send_json({"type": "input_audio_buffer.speech_started"})
                            # Barge-in: only cancel if a response is actually active
                            if response_active:
                                try:
                                    await rt_ws.send(
                                        json.dumps({"type": "response.cancel"})
                                    )
                                except Exception:
                                    pass

                        elif event_type == "input_audio_buffer.speech_stopped":
                            await ws.send_json({"type": "input_audio_buffer.speech_stopped"})

                        elif event_type == "conversation.item.input_audio_transcription.completed":
                            await ws.send_json(
                                {
                                    "type": "input_audio_transcription.done",
                                    "transcript": event.get("transcript", ""),
                                }
                            )

                        elif event_type == "response.function_call_arguments.done":
                            response_active = True
                            fn_name = event.get("name", "")
                            call_id = event.get("call_id", "")
                            arguments = event.get("arguments", "")

                            # Handle end_session specially
                            if fn_name == "end_session":
                                await rt_ws.send(
                                    json.dumps(
                                        {
                                            "type": "conversation.item.create",
                                            "item": {
                                                "type": "function_call_output",
                                                "call_id": call_id,
                                                "output": "Session ended. Goodbye!",
                                            },
                                        }
                                    )
                                )
                                await ws.send_json({"type": "session.end"})
                                return

                            # Check if this is a long-running function
                            if fn_name in BACKGROUND_FUNCTIONS:
                                # Return immediately with "started" message
                                bg_task = task_mgr.create_task(fn_name, f"Running {fn_name}")
                                logger.info("Starting background task for %s (task=%s)", fn_name, bg_task.id)

                                await ws.send_json({
                                    "type": "agent.activity",
                                    "action": fn_name,
                                    "status": "started",
                                })

                                # Send quick response so voice can continue
                                started_output = json.dumps({
                                    "status": "started_in_background",
                                    "message": f"I've started {fn_name} in the background. "
                                    "I'll let you know as soon as it's done. "
                                    "Feel free to ask me anything else in the meantime.",
                                })
                                await rt_ws.send(json.dumps({
                                    "type": "conversation.item.create",
                                    "item": {
                                        "type": "function_call_output",
                                        "call_id": call_id,
                                        "output": started_output,
                                    },
                                }))
                                await rt_ws.send(json.dumps({"type": "response.create"}))

                                # Run the actual function in background
                                asyncio.create_task(
                                    _run_background_task(
                                        task_mgr, _supervisor, fn_name, call_id, arguments, bg_task.id
                                    )
                                )
                            else:
                                # Synchronous: run inline as before
                                logger.info("Sending agent.activity started for %s", fn_name)
                                await ws.send_json({
                                    "type": "agent.activity",
                                    "action": fn_name,
                                    "status": "started",
                                })

                                result = await handle_voice_function_call(
                                    _supervisor, fn_name, call_id, arguments
                                )
                                logger.info("Function %s result: %s", fn_name, result["output"][:100])

                                logger.info("Sending agent.activity completed for %s", fn_name)
                                await ws.send_json({
                                    "type": "agent.activity",
                                    "action": fn_name,
                                    "status": "completed",
                                    "agent": result.get("agent", "Agent"),
                                    "output": result["output"][:200],
                                })

                                await rt_ws.send(
                                    json.dumps({
                                        "type": "conversation.item.create",
                                        "item": {
                                            "type": "function_call_output",
                                            "call_id": call_id,
                                            "output": result["output"],
                                        },
                                    })
                                )
                                await rt_ws.send(
                                    json.dumps({"type": "response.create"})
                                )

                        elif event_type == "response.done":
                            response_active = False
                            await ws.send_json({"type": "response.done"})

                        elif event_type == "error":
                            error_info = event.get("error", {})
                            error_code = error_info.get("code", "")
                            # Don't forward non-fatal errors (e.g. cancel when no response)
                            if error_code in ("response_cancel_not_active",):
                                logger.debug("Non-fatal Realtime error: %s", error_code)
                            else:
                                logger.error("Realtime API error: %s", event)
                                await ws.send_json(
                                    {
                                        "type": "error",
                                        "message": error_info.get("message", "Unknown error"),
                                    }
                                )

                except websockets.ConnectionClosed:
                    logger.info("Realtime WebSocket closed")
                except Exception:
                    logger.exception("Error receiving from Realtime API")

            # Run all directions concurrently (including background task poller)
            poller = asyncio.create_task(poll_background_completions())
            try:
                await asyncio.gather(
                    receive_from_client(),
                    receive_from_realtime(),
                    return_exceptions=True,
                )
            finally:
                poller.cancel()

    except WebSocketDisconnect:
        logger.info("Voice WebSocket disconnected")
    except Exception:
        logger.exception("Voice WebSocket error")
        try:
            await ws.send_json({"type": "error", "message": "Voice session failed to connect"})
        except Exception:
            pass
