"""Notes Agent — specialist agent for note CRUD operations."""

import json
import logging

from app.models.note import NoteCreate, NoteUpdate
from app.services.notes_service import NotesService

logger = logging.getLogger(__name__)


class NotesAgent:
    """Agent that handles notes operations by delegating to NotesService."""

    def __init__(self, notes_service: NotesService):
        self._service = notes_service

    @property
    def tool_definitions(self) -> list[dict]:
        """Return OpenAI-compatible function tool definitions."""
        return [
            {
                "type": "function",
                "function": {
                    "name": "create_note",
                    "description": "Create a new note with a title and content",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "title": {"type": "string", "description": "The note title"},
                            "content": {"type": "string", "description": "The note content"},
                        },
                        "required": ["title", "content"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "get_notes",
                    "description": "List all notes for the user",
                    "parameters": {"type": "object", "properties": {}},
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "get_note",
                    "description": "Get a specific note by its ID",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "note_id": {"type": "string", "description": "The note ID"},
                        },
                        "required": ["note_id"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "update_note",
                    "description": "Update an existing note's title and/or content",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "note_id": {"type": "string", "description": "The note ID to update"},
                            "title": {"type": "string", "description": "New title (optional)"},
                            "content": {
                                "type": "string",
                                "description": "New content (optional)",
                            },
                        },
                        "required": ["note_id"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "delete_note",
                    "description": "Delete a note by its ID",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "note_id": {"type": "string", "description": "The note ID to delete"},
                        },
                        "required": ["note_id"],
                    },
                },
            },
        ]

    async def handle_function_call(self, function_name: str, arguments: str, user_id: str = "default-user") -> str:
        """Execute a function call and return the result as a string."""
        try:
            args = json.loads(arguments) if arguments else {}
        except json.JSONDecodeError:
            return json.dumps({"error": "Invalid arguments"})

        service = self._service.with_user(user_id) if hasattr(self._service, 'with_user') else self._service

        if function_name == "create_note":
            note = await service.create(
                NoteCreate(title=args["title"], content=args["content"])
            )
            if note:
                return json.dumps(
                    {"success": True, "note": {"id": note.id, "title": note.title}},
                )
            return json.dumps({"error": "Failed to create note"})

        elif function_name == "get_notes":
            notes = await service.list()
            return json.dumps(
                {
                    "notes": [
                        {"id": n.id, "title": n.title, "content": n.content[:100]}
                        for n in notes
                    ]
                },
            )

        elif function_name == "get_note":
            note = await service.get_by_id(args["note_id"])
            if note:
                return json.dumps(
                    {"note": {"id": note.id, "title": note.title, "content": note.content}},
                )
            return json.dumps({"error": "Note not found"})

        elif function_name == "update_note":
            update = NoteUpdate(title=args.get("title"), content=args.get("content"))
            note = await service.update(args["note_id"], update)
            if note:
                return json.dumps(
                    {"success": True, "note": {"id": note.id, "title": note.title}},
                )
            return json.dumps({"error": "Note not found"})

        elif function_name == "delete_note":
            deleted = await service.delete(args["note_id"])
            return json.dumps({"success": deleted})

        return json.dumps({"error": f"Unknown function: {function_name}"})
