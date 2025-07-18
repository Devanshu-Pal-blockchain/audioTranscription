# Todos and Issues API Documentation

## Overview
This implementation adds two new collections to the audioTranscription backend:
- **Todos**: Short-term action items (due within 14 days)
- **Issues**: Problems or discussion bottlenecks raised during meetings

Both collections follow the same patterns as existing collections (rocks, tasks, etc.) with UUID primary keys, async functions, and proper authentication.

## Database Collections
- `db.todos` - Stores todo documents
- `db.issues` - Stores issue documents

## Models

### Todo Model
```python
{
    "todo_id": "UUID",           # Primary key
    "task_title": "string",      # Title of the todo
    "assigned_to": "string",     # Full name of assigned person
    "designation": "string",     # Job title
    "due_date": "date",         # Due date (YYYY-MM-DD)
    "linked_issue": "string?",   # Optional reference to related issue
    "status": "string",         # pending, in_progress, completed
    "quarter_id": "UUID",       # Reference to quarter
    "assigned_to_id": "UUID?",  # UUID of assigned user (if found)
    "created_at": "datetime",
    "updated_at": "datetime"
}
```

### Issue Model
```python
{
    "issue_id": "UUID",              # Primary key
    "issue_title": "string",         # Title of the issue
    "description": "string",         # Detailed description
    "raised_by": "string",           # Full name who raised it
    "discussion_notes": "string?",   # Optional discussion points
    "linked_solution_type": "string?", # rock, todo, runtime_solution
    "linked_solution_ref": "string?",  # Reference to solution
    "status": "string",              # open, in_progress, resolved
    "quarter_id": "UUID",           # Reference to quarter
    "raised_by_id": "UUID?",        # UUID of person who raised it
    "created_at": "datetime",
    "updated_at": "datetime"
}
```

## API Endpoints

### Todos API (`/todos`)

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| POST | `/todos` | Create new todo | Yes |
| GET | `/todos/{todo_id}` | Get todo by ID | Yes |
| GET | `/quarters/{quarter_id}/todos` | Get todos by quarter | Yes |
| GET | `/users/{user_id}/todos` | Get todos by user | Yes |
| GET | `/todos?status={status}&quarter_id={id}` | Get todos by status | Yes |
| PUT | `/todos/{todo_id}` | Update todo | Yes |
| DELETE | `/todos/{todo_id}` | Delete todo | Facilitator only |
| GET | `/todos/overdue` | Get overdue todos | Yes |
| GET | `/todos/due-soon?days=7` | Get todos due soon | Yes |
| GET | `/todos/statistics?quarter_id={id}` | Get todo statistics | Facilitator only |

### Issues API (`/issues`)

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| POST | `/issues` | Create new issue | Yes |
| GET | `/issues/{issue_id}` | Get issue by ID | Yes |
| GET | `/quarters/{quarter_id}/issues` | Get issues by quarter | Yes |
| GET | `/users/{user_id}/issues` | Get issues by user | Yes |
| GET | `/issues?status={status}&quarter_id={id}` | Get issues by status | Yes |
| GET | `/issues/solution-type/{type}?quarter_id={id}` | Get issues by solution type | Yes |
| GET | `/issues/search?q={query}&quarter_id={id}` | Search issues | Yes |
| PUT | `/issues/{issue_id}` | Update issue | Yes |
| DELETE | `/issues/{issue_id}` | Delete issue | Facilitator only |
| GET | `/issues/statistics?quarter_id={id}` | Get issue statistics | Facilitator only |

## Pipeline Integration

The pipeline now automatically creates todos and issues when processing meeting transcriptions:

1. **Audio Processing** → **Semantic Tokenization** → **Segment Analysis** → **ROCKS Generation**
2. The ROCKS generation step produces a JSON response containing `todos` and `issues` arrays
3. **Data Parser Service** processes these arrays and:
   - Assigns UUIDs to each todo/issue
   - Maps participant names to user IDs when possible
   - Sets appropriate timestamps and statuses
   - Saves to both JSON files and database collections

## File Structure
```
Backend/
├── models/
│   ├── todo.py          # Todo model and PipelineTodo
│   └── issue.py         # Issue model and PipelineIssue
├── service/
│   ├── todo_service.py  # Todo business logic
│   ├── issue_service.py # Issue business logic
│   └── base_service.py  # Updated with todos/issues collections
├── routes/
│   ├── todo.py          # Todo API endpoints
│   └── issue.py         # Issue API endpoints
└── main.py              # Updated to include new routes
```

## Authentication & Permissions

### Todos
- **Create**: Any authenticated user
- **Read**: Users can see their own todos + Facilitators see all
- **Update**: Users can update their own todos + Facilitators can update any
- **Delete**: Facilitator only

### Issues
- **Create**: Any authenticated user
- **Read**: All authenticated users can see all issues
- **Update**: Issue raiser + Facilitators can update
- **Delete**: Facilitator only

## Usage Examples

### Create Todo
```bash
POST /todos
{
    "task_title": "Complete budget review",
    "assigned_to": "John Doe",
    "designation": "Finance Manager",
    "due_date": "2024-03-15",
    "quarter_id": "uuid-here"
}
```

### Create Issue
```bash
POST /issues
{
    "issue_title": "Resource allocation bottleneck",
    "description": "Team capacity constraints affecting delivery",
    "raised_by": "Jane Smith",
    "quarter_id": "uuid-here"
}
```

### Search Issues
```bash
GET /issues/search?q=resource&quarter_id=uuid-here
```

### Get Statistics
```bash
GET /todos/statistics?quarter_id=uuid-here
# Returns: total, completed, pending, in_progress, overdue, completion_rate

GET /issues/statistics?quarter_id=uuid-here  
# Returns: total, open, in_progress, resolved, resolution_rate, solution_types
```

## Integration with Existing Code

- **Consistent patterns**: Follows same UUID-based primary keys, async functions, and error handling as existing collections
- **Authentication**: Uses same auth system (`get_current_user`, `Facilitator_required`)
- **Database**: Uses same base service pattern with MongoDB collections
- **Pipeline**: Integrates seamlessly with existing pipeline processing
- **API structure**: Follows same RESTful conventions as rocks/tasks APIs
