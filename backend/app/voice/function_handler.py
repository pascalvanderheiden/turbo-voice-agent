"""Function call handler — bridges Voice Live function calls to the supervisor agent."""

import logging

from app.agents.supervisor import SupervisorAgent

logger = logging.getLogger(__name__)


async def handle_voice_function_call(
    supervisor: SupervisorAgent,
    function_name: str,
    call_id: str,
    arguments: str,
) -> dict:
    """Handle a function call from Voice Live by routing through the supervisor.

    Returns a dict suitable for sending back as a FunctionCallOutputItem.
    """
    logger.info("Voice function call: %s (call_id=%s)", function_name, call_id)

    try:
        result, agent_name = await supervisor.handle_function_call(function_name, arguments)
        return {
            "type": "function_call_output",
            "call_id": call_id,
            "output": result,
            "agent": agent_name,
        }
    except Exception:
        logger.exception("Error handling function call: %s", function_name)
        return {
            "type": "function_call_output",
            "call_id": call_id,
            "output": '{"error": "An error occurred processing your request. Please try again."}',
        }
