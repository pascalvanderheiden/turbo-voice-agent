## ADDED Requirements

### Requirement: Todos page
The frontend SHALL provide a `/todos` page accessible from the sidebar navigation that displays the user's Microsoft To-Do tasks with list and detail views.

#### Scenario: User views todo list
- **WHEN** the user navigates to `/todos`
- **THEN** the page SHALL load and display all tasks from Microsoft To-Do via `GET /api/todos`, showing title, completion status, and due date (if set)

#### Scenario: Empty state when no todos exist
- **WHEN** the user has no tasks in Microsoft To-Do
- **THEN** the page SHALL display an empty state message encouraging the user to create their first to-do

#### Scenario: User not connected to Microsoft To-Do
- **WHEN** the user navigates to `/todos` but has not connected their Microsoft Account
- **THEN** the page SHALL display a prompt to connect Microsoft To-Do with a link/button to the connection flow in the user menu

### Requirement: Create todo from UI
The user SHALL be able to create a new to-do task from the todos page.

#### Scenario: User creates a todo
- **WHEN** the user clicks "Create" and submits a title (and optional due date, notes)
- **THEN** the system SHALL call `POST /api/todos` which creates the task in Microsoft To-Do and the new task appears in the list

### Requirement: Edit todo from UI
The user SHALL be able to edit an existing to-do task's title, notes, and due date.

#### Scenario: User edits a todo
- **WHEN** the user selects a task, modifies its fields, and saves
- **THEN** the system SHALL call `PUT /api/todos/{id}` which updates the task in Microsoft To-Do

### Requirement: Complete todo from UI
The user SHALL be able to mark a to-do task as complete or incomplete directly from the list view.

#### Scenario: User completes a todo
- **WHEN** the user clicks the completion checkbox on a task
- **THEN** the system SHALL call `PUT /api/todos/{id}` with `isCompleted: true` and the task SHALL visually update to show completed state (strikethrough, muted styling)

#### Scenario: User uncompletes a todo
- **WHEN** the user clicks the completion checkbox on a completed task
- **THEN** the system SHALL call `PUT /api/todos/{id}` with `isCompleted: false` and the task SHALL return to active styling

### Requirement: Delete todo from UI
The user SHALL be able to delete a to-do task.

#### Scenario: User deletes a todo
- **WHEN** the user confirms deletion of a task
- **THEN** the system SHALL call `DELETE /api/todos/{id}` which removes the task from Microsoft To-Do

### Requirement: Backend REST routes for todos
The system SHALL provide REST routes at `/api/todos` that proxy operations through the TodoAgent to the MCP server. No data is stored in Cosmos DB.

#### Scenario: List todos via REST
- **WHEN** `GET /api/todos` is called with a valid authenticated user
- **THEN** the route SHALL call `todo_agent.handle_function_call("get_todos", ...)` and return the task list

#### Scenario: Create todo via REST
- **WHEN** `POST /api/todos` is called with `{"title": "...", "dueDate": "...", "notes": "..."}`
- **THEN** the route SHALL call `todo_agent.handle_function_call("create_todo", ...)` and return the created task

#### Scenario: REST returns 503 when not connected
- **WHEN** any `/api/todos` route is called but the user has not connected Microsoft To-Do
- **THEN** the route SHALL return HTTP 503 with `{"detail": "Microsoft To-Do is not connected"}`

### Requirement: Frontend API client for todos
The frontend SHALL provide a `todosApi` object in `lib/api.ts` with typed functions for all to-do operations, plus a `connectionsApi` object for Microsoft To-Do connection management.

#### Scenario: API client provides CRUD methods
- **WHEN** the todosApi is imported
- **THEN** it SHALL expose `list()`, `get(id)`, `create(data)`, `update(id, data)`, `delete(id)` methods following the established pattern

#### Scenario: Connections API provides status and connect methods
- **WHEN** the connectionsApi is imported
- **THEN** it SHALL expose `microsoftTodo.status()`, `microsoftTodo.connect()`, `microsoftTodo.disconnect()` methods
