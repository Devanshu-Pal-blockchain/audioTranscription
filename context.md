# Meeting Transcription and Goal Management System

## Project Vision
This project aims to create an enterprise-level meeting management and goal tracking system, primarily focused on C-level executive meetings. The system automatically records, transcribes, and processes meeting audio to extract structured information about organizational goals (rocks), tasks, and subtasks.

## Target Users
- Primary: C-level executives (CEO, COO, etc.)
- Organization-level implementation (not project-level)
- Enterprise companies conducting quarterly planning meetings

## Core Functionality Flow
1. **Meeting Recording**
   - Frontend capability to record meeting audio
   - Integration with platforms like Google Meet (planned)
   - Audio capture and storage

2. **Transcription Process**
   - Convert meeting audio to raw JSON transcript
   - Process raw transcript into structured, articulated JSON
   - No waste data - all transcript content is utilized

3. **Goal Management**
   - Hierarchy: Quarter → Rocks → Tasks → Subtasks
   - Rocks (Goals) are set quarterly
   - Each Rock has a duration (default: quarter length in weeks)
   - Tasks are assigned to specific weeks
   - Subtasks are optional and task-specific

## Technical Architecture

### Backend Technology Stack
- FastAPI framework for API development
- Python 3.x
- JWT for access token authentication
- Pydantic for data validation and schema definitions
- MongoDB for database (using motor for async operations)

### Backend Structure
- Focus on routes/ and service/ directories
- Clean separation of concerns
- RAG/LLM/Langchain code remains untouched (not in current scope)
- New `models/` directory for Pydantic schema definitions
- Separate files for each model schema
- No nested class definitions allowed
- All APIs protected with JWT access tokens
- CRUD operations available for all collection fields

### Database Collections and Schemas

#### 1. Quarter Collection
```typescript
{
  quarter_id: UUID,          // Backend-generated UUID
  quarter: string,           // Q1, Q2, Q3, Q4
  weeks: number,            // Number of weeks in quarter (e.g., 12)
  year: number,             // Single year (e.g., 2024)
  title: string,            // Quarter title
  description: string,      // Quarter description
  participants: UUID[],     // Array of participant IDs
  status: number,          // 0 = draft, 1 = saved
  created_at: Date,        // Creation timestamp
  updated_at: Date         // Last update timestamp
}
```

#### 2. Rock Collection
```typescript
{
  rock_id: UUID,            // Backend-generated UUID
  rock_name: string,        // Goal/objective name
  smart_objective: string,  // Detailed SMART objective
  quarter_id: UUID,         // Reference to Quarter collection
  assigned_to_id: UUID,     // Owner's ID
  assigned_to_name: string  // Owner's name
}
```

#### 3. Task Collection
```typescript
{
  rock_id: UUID,            // Reference to Rock collection
  week: number,             // Week number (1-12)
  task_id: UUID,            // Backend-generated UUID
  task: string,             // Task description
  sub_tasks?: {             // Optional sub-tasks
    // TBD structure
  },
  comments: {
    comment_id: UUID,
    commented_by: string    // Employee ID/name who commented
  }
}
```

#### 4. Users Collection
```typescript
{
  employee_id: UUID,        // Backend-generated UUID
  employee_name: string,    // Employee name
  employee_email: string,   // Email address
  employee_password: string, // Hashed password
  employee_role: "admin" | "employee", // Role type
  assigned_rocks: UUID[]    // Two-way reference with Rock collection
}
```

#### 5. Transcript Collection
- Maintain existing raw transcript collection structure
- No modifications needed to current implementation

### Key Database Rules
1. All IDs must be UUIDs (never use ObjectId)
2. Always remove ObjectId from database responses
3. Two-way mappings:
   - Quarter ↔ Rock (via quarter_id)
   - Rock ↔ Task (via rock_id)
   - Rock ↔ User (via assigned_to_id and assigned_rocks)

### Business Rules
1. One rock can only be assigned to one person
2. One person can have multiple rocks assigned
3. All tasks under a rock are automatically associated with the rock's assignee
4. Week numbers must correspond to the parent quarter's total weeks

## Development Guidelines
1. Focus only on immediate tasks
2. Do not modify unrelated code
3. Maintain professional approach and flow
4. Regular context.md updates
5. Follow task checklist rigorously
6. Always remove ObjectId from database responses
7. Use UUID for all ID fields

## Implementation Checklist
- [ ] Create models/ directory
- [ ] Implement Quarter schema
- [ ] Implement Rock schema
- [ ] Implement Task schema
- [ ] Implement User schema
- [ ] Verify UUID usage across all schemas
- [ ] Implement ObjectId removal middleware
- [ ] Create service layer for each collection
- [ ] Implement API routes for each collection
- [ ] Add validation for business rules
- [ ] Test two-way mappings
- [ ] Document API endpoints

## Context.md File Management
- Review after every prompt/command
- Update with any new information
- Document all decisions and discussions
- Track implementation progress
- Note any schema changes or refinements
- Document business rule clarifications
- Track API endpoint development

## Important Reminders
- Never modify transcript collection code
- Always use UUIDs, never ObjectId
- Remove ObjectId from all database responses
- Maintain two-way references
- Follow schema definitions exactly
- Document all changes in context.md
- Check context.md before starting new work
- Focus on one task at a time

### Implementation Requirements
1. Authentication:
   - JWT access token required for all endpoints
   - Token validation middleware
   - Admin-level access control

2. API Structure:
   - CRUD operations for all collections
   - Consistent error handling
   - Input validation using Pydantic
   - Response serialization
   - ObjectId removal middleware

3. Code Organization:
   - Flat class structure (no nested classes)
   - Clear separation of concerns
   - Modular service layer
   - Consistent naming conventions
   - Type hints throughout the codebase

## Implementation Progress

### Completed
1. Models Implementation
   - Removed unnecessary base and config files
   - Each model is self-contained with no nested classes
   - Using Pydantic v2 ConfigDict for configuration
   - All models include:
     - UUID fields for IDs
     - Created/Updated timestamps
     - Field validations
     - Example data
     - ObjectId removal
   - Implemented models:
     - Quarter (quarter.py)
     - Rock (rock.py)
     - Task and Comment (task.py)
     - User (user.py)

2. Database Setup
   - Configured async MongoDB connection using Motor
   - Environment-based configuration
   - Proper error handling for missing configuration

3. Service Layer Implementation
   - All services use async functions exclusively
   - Implemented QuarterService:
     - CRUD operations
     - Participant management
     - Async operations
     - Cascading rock deletion
     - Participant tracking
   - Implemented RockService:
     - CRUD operations
     - Quarter-based queries
     - Assignment management
     - Two-way user references
     - Async operations
   - Implemented TaskService:
     - CRUD operations
     - Rock-based task queries
     - Week-based task queries
     - Rock existence validation
     - Subtask management
     - Comment management
     - Async operations
   - Implemented UserService:
     - CRUD operations
     - Password hashing and verification
     - Role-based queries
     - Rock assignment management
     - Email-based lookups
     - Async operations

4. Authentication System
   - JWT token implementation with jose library
   - Async authentication service
   - Password hashing with bcrypt
   - Token-based user identification
   - Role-based access control
   - Token expiration (30 minutes)
   - Login endpoint with OAuth2
   - Admin-only route protection
   - User session management
   - Secure password handling

5. API Routes Implementation
   - Protected endpoints for all collections
   - JWT authentication integration
   - Role-based access control
   - Input validation using Pydantic
   - Standardized error responses
   - Proper error status codes
   - Resource-based access control
   - Field-specific update endpoints
   - Status-based filtering
   - Implemented routes:
     - Quarter routes:
       - CRUD operations
       - Participant management
       - Field-specific updates (weeks, year, title, description, status)
       - Status-based filtering
       - Draft/saved state management
     - Rock routes (CRUD + assignment management)
     - Task routes (CRUD + subtasks + comments)
     - User routes (CRUD + password management)
     - Auth routes (login + token generation)
   - Route features:
     - Async operations
     - Protected endpoints
     - Input validation
     - Error handling
     - Access control
     - Response serialization

### Code Structure Principles
1. No Nested Classes
   - Each model is a standalone class
   - Configuration is done via model_config attribute
   - No inheritance between models
   - Clean, flat structure

2. Model Features
   - UUID for all IDs
   - Automatic timestamps
   - Field validation
   - Type hints
   - Documentation
   - Example data
   - ObjectId removal
   - Password field protection

3. Service Layer Features
   - All functions are async
   - Async operations with Motor
   - Type-safe interfaces
   - Comprehensive error handling
   - Business logic encapsulation
   - Clean method organization
   - Password security with bcrypt
   - MongoDB query optimization
   - Proper type hints and documentation
   - Two-way reference maintenance
   - Cascading deletions
   - Cross-collection validation
   - Relationship integrity checks
   - Field-specific updates
   - Status management (draft/saved)
   - Filtered queries by status
   - Individual field validation

4. Authentication Features
   - Async token generation and validation
   - Secure password hashing
   - Role-based middleware
   - Token payload encryption
   - User session tracking
   - OAuth2 password flow
   - Admin privilege checks
   - Email-based authentication
   - Token expiration handling
   - Proper error responses

### Relationship Management
1. Quarter ↔ Rock
   - Rocks are linked to quarters via quarter_id
   - Deleting a quarter cascades to rocks
   - Quarter queries include rock access
   - Rock creation validates quarter

2. Rock ↔ User
   - Two-way reference maintained
   - User.assigned_rocks ↔ Rock.assigned_to_id
   - Assignment changes update both collections
   - Deletion cleans up both sides

3. Rock ↔ Task
   - Tasks are linked to rocks via rock_id
   - Rock existence validated on task operations
   - Task queries by rock and week
   - Rock deletion cascades to tasks

4. User Relationships
   - Quarter participation tracking
   - Rock assignments with two-way refs
   - Task inheritance through rock assignment
   - Role-based access control

### Business Rules Implementation
1. Rock Assignment
   - One rock has one assignee (enforced by schema)
   - One user can have multiple rocks (array in user doc)
   - Assignment changes maintain both sides
   - Clean reference management

2. Task Management
   - Tasks inherit rock's assignee
   - Week numbers validated against quarter
   - Subtasks are optional and flexible
   - Comments track authorship

3. Quarter Structure
   - Weeks correspond to quarter duration
   - Participant list maintained
   - Rock associations tracked
   - Cascading deletions

### In Progress
1. API Routes
   - Protected endpoints for all collections
   - Input validation
   - Response formatting
   - Error handling

## Next Steps
1. Testing and Documentation:

   - Unit tests for services
   - Integration tests for APIs
   - API documentation
   - Deployment guide
   - Security review
   - Performance testing

2. Frontend Integration:
   - API client implementation
   - Authentication flow
   - Error handling
   - Form validation
   - Real-time updates

# Backend Implementation Details

## Access Control

### Latest Updates

#### Access Control Refinements
1. Admin Access:
   - Full access to all data and operations
   - Can view and manage all quarters, rocks, and tasks
   - Can add admin comments on tasks
   - Can manage user roles and assignments
   - Can perform bulk operations

2. Regular User Access:
   - View only assigned rocks and their tasks
   - Comment only on assigned tasks
   - Cannot add/modify admin comments
   - Limited to their own data in combined operations
   - Personal dashboard view

#### Combined Operations
1. Quarter-level Operations:
   ```typescript
   GET /quarters/{quarter_id}/all
   {
     quarter: QuarterData,
     rocks: RockWithTasks[],
     total_rocks: number,
     total_tasks: number
   }
   ```

2. Rock-level Operations:
   ```typescript
   GET /rocks/{rock_id}/tasks
   {
     rock: RockData,
     tasks: TaskWithComments[],
     total_tasks: number
   }
   ```

3. User Dashboard:
   ```typescript
   GET /users/{user_id}/dashboard
   {
     user: UserData,
     quarters: QuarterWithRocksAndTasks[],
     total_quarters: number,
     total_rocks: number,
     total_tasks: number
   }
   ```

4. Week-specific Views:
   ```typescript
   GET /quarters/{quarter_id}/week/{week}
   {
     quarter: QuarterData,
     week: number,
     rocks: RockWithWeekTasks[],
     total_rocks: number,
     total_tasks: number
   }
   ```

#### Admin Comments System
1. Comment Structure:
   ```typescript
   {
     comment_id: UUID,
     commented_by: string,
     content: string,
     created_at: Date,
     is_admin_comment: boolean
   }
   ```

2. Comment Rules:
   - Only admins can add/edit/delete admin comments
   - Regular users can only manage their own comments
   - Comments tied to task ownership
   - Optional comment loading in combined operations

#### Bulk Operations
1. Task Management:
   ```typescript
   POST /tasks/bulk
   PUT /tasks/bulk
   DELETE /tasks/bulk
   ```

2. Quarter Data:
   ```typescript
   POST /quarters/{quarter_id}/bulk
   {
     rocks: Rock[],
     tasks_by_rock: { [rock_id: string]: Task[] }
   }
   ```

#### Frontend Support
1. Card Structure:
   - Quarter cards with rock summaries
   - Rock cards with weekly task breakdowns
   - Task cards with comments and subtasks
   - Admin comment indicators

2. Data Loading:
   - Optional comment loading
   - Week-specific data loading
   - Role-based data filtering
   - Combined data fetching

#### Implementation Notes
1. Access Control:
   - JWT authentication required for all endpoints
   - Role-based access checks in routes
   - Data filtering based on user role
   - Ownership validation for operations

2. Data Consistency:
   - Cascading updates/deletes
   - Two-way reference maintenance
   - Week number validation
   - Comment ownership tracking

3. Error Handling:
   - Detailed error messages
   - Proper HTTP status codes
   - Validation error responses
   - Operation result summaries

4. Performance:
   - Optional data loading
   - Bulk operation support
   - Efficient combined queries
   - Proper indexing (MongoDB)

## Collections and Services

### Combined Operations (CombinedService)

1. Quarter-Rock-Task Operations:
   - Get all rocks + tasks for a quarter (admin)
   - Get user-specific rocks + tasks for a quarter
   - Get specific rock + all tasks for a quarter
   - Get specific rock + specific task for a quarter
   - CRUD operations for each combination
   - Optional user data inclusion
   - Dropdown support for quarter selection

2. Quarter Data Operations:
   - `get_quarter_data`: Get all data for a quarter (admin)
   - `get_quarter_data_for_user`: Get user-specific data
   - All rocks in the quarter (filtered by access)
   - All tasks for each rock
   - Assigned user details
   - Optional comment inclusion
   - Total rock count

3. Admin Comment Operations:
   - Add admin comments to tasks
   - Update admin comments
   - Delete admin comments
   - View all comments (admin)
   - View task-specific comments (user)

4. Rock-Task Operations:
   - Get all tasks for a rock
   - Update specific task in a rock
   - Create new tasks for a rock
   - Delete tasks from a rock
   - Optional comment inclusion

5. Quarter-Rock-Task-User Operations:
   - Get user assignments for rocks
   - Get user assignments for tasks
   - Update assignments (admin)
   - Delete assignments (admin)

### Rock Collection

1. Basic CRUD Operations:
   - Create rock (admin)
   - Get rock by ID (filtered by access)
   - Update rock (admin)
   - Delete rock (admin)

2. Quarter-specific Operations:
   - Get rock by quarter ID
   - Get all rocks in a quarter
   - Update rock in quarter
   - Delete rock from quarter

3. Smart Objective Operations:
   - Update SMART objective (admin)
   - Get SMART objective

4. Assignment Operations:
   - Assign rock to user (admin)
   - Unassign rock from user (admin)
   - Get assignment info
   - Get rocks by user

### Task Collection

1. Basic CRUD Operations:
   - Create task (admin)
   - Get task by ID (filtered by access)
   - Update task (admin)
   - Delete task (admin)

2. Week-specific Operations:
   - Create task for week
   - Update task for week
   - Delete task for week
   - Get tasks by week

3. Comment Operations:
   - Add admin comment (admin only)
   - Update admin comment (admin only)
   - Delete admin comment (admin only)
   - View comments (filtered by access)
   - Update comment author (admin only)

4. Rock-specific Operations:
   - Get tasks by rock
   - Create task for rock
   - Update task in rock
   - Delete task from rock

### User Collection

1. Basic CRUD Operations:
   - Create user (admin)
   - Get user by ID
   - Update user (admin/self)
   - Delete user (admin)

2. Field-specific Operations:
   - Update name (admin/self)
   - Update email (admin/self)
   - Update password (admin/self)
   - Update role (admin)
   - Get user profile

3. Rock Assignment Operations:
   - Assign rock to user (admin)
   - Unassign rock from user (admin)
   - Get assigned rocks
   - Get users by rock (admin)

## API Features

1. Dropdown Support:
   - Quarter selection affects all data
   - Data filtered by user access
   - Cascading updates for rocks and tasks
   - User assignment updates

2. Data Loading Options:
   - With/without comments
   - With/without user details
   - Full/partial task data
   - Access-controlled data

3. Combined Operations:
   - Quarter + Rock operations
   - Quarter + Rock + Task operations
   - Rock + Task operations
   - User assignment operations
   - Admin-specific operations

4. Validation and Security:
   - Quarter ownership validation
   - Rock-Task relationship validation
   - User assignment validation
   - Email uniqueness check
   - Password hashing
   - Role-based access control

5. Error Handling:
   - Not found errors
   - Invalid relationship errors
   - Duplicate assignment errors
   - Invalid data errors
   - Authorization errors

## Implementation Notes

1. Two-way References:
   - User-Rock assignments
   - Rock-Task relationships
   - Quarter-Rock relationships
   - Admin-Comment relationships

2. Timestamps:
   - Created at
   - Updated at
   - Comment timestamps
   - All operations update timestamps

3. Data Consistency:
   - Cascading deletes
   - Reference cleanup
   - Assignment validation
   - Comment ownership

4. Performance:
   - Optional comment loading
   - Selective user data inclusion
   - Efficient combined queries
   - Access-filtered queries

5. Frontend Support:
   - Dropdown data loading
   - Combined data fetching
   - Assignment management
   - Task organization
   - Role-based UI adaptation

6. Admin Features:
   - Task commenting system
   - User management
   - Assignment control
   - Full data access
   - Bulk operations

7. User Features:
   - Personal data access
   - Task viewing
   - Comment viewing
   - Profile management
   - Assignment viewing

# API Documentation

## Combined Data APIs

### User-Based APIs
1. GET `/users/{user_id}/dashboard`
   - Get user's complete dashboard data including quarters, rocks, and tasks
   - Optional: `include_comments=true/false`
   - Access: Admin or self only

2. GET `/users/{user_id}/rocks/all`
   - Get all rocks assigned to a user with their tasks
   - Optional: `include_comments=true/false`
   - Access: Admin or self only

3. GET `/users/{user_id}/current-quarter`
   - Get user's current quarter data with rocks and tasks
   - Optional: `include_comments=true/false`
   - Access: Admin or self only

4. GET `/users/{user_id}/week/{week}`
   - Get user's tasks for a specific week
   - Optional: `include_comments=true/false`
   - Access: Admin or self only

### Quarter-Based APIs
1. GET `/quarters/{quarter_id}/all`
   - Get quarter with all rocks and tasks
   - Optional: `include_comments=true/false`
   - Access: All authenticated users (filtered by role)

2. GET `/quarters/{quarter_id}/week/{week}`
   - Get quarter's tasks for a specific week
   - Optional: `include_comments=true/false`
   - Access: All authenticated users (filtered by role)

3. GET `/quarters/user/{user_id}/all`
   - Get all quarters with rocks and tasks for a user
   - Optional: `include_comments=true/false`
   - Access: Admin or self only

### Rock-Based APIs
1. GET `/rocks/{rock_id}/tasks`
   - Get rock with all its tasks
   - Optional: `include_comments=true/false`
   - Access: Admin or assigned user only

2. GET `/rocks/quarter/{quarter_id}/all`
   - Get all rocks in a quarter with their tasks
   - Optional: `include_comments=true/false`
   - Access: All authenticated users (filtered by role)

### Bulk Operations
1. POST `/quarters/{quarter_id}/bulk`
   - Bulk create rocks and tasks for a quarter
   - Admin only

2. POST `/rocks/bulk`
   - Bulk create rocks and their tasks
   - Admin only

## Access Control
- Admins have full access to all data
- Regular users can only access:
  - Their own profile and dashboard
  - Quarters they are participants in
  - Rocks assigned to them
  - Tasks in their assigned rocks
  - Comments on their tasks (if included)

## Data Relationships
1. Quarter → Rock:
   - Two-way referencing
   - Quarter has rock_ids
   - Rock has quarter_id

2. Rock → Task:
   - Two-way referencing
   - Rock has task_ids
   - Task has rock_id

3. User → Rock:
   - Two-way referencing
   - User has assigned_rock_ids
   - Rock has assigned_to field (id and name)

4. Quarter → User:
   - Two-way referencing
   - Quarter has participant_ids
   - User has quarter_ids

## Week Management
- All collections (Quarter, Rock, Task) include week information
- Week-specific views available through dedicated endpoints
- Tasks can be filtered and grouped by week
- Week numbers are consistent across collections

## Comments System
- Comments are part of Task collection
- Optional loading through include_comments parameter
- Admin-only comments feature
- Comment ownership tracking
- Access control based on task ownership

---
Last Updated: [Current Date]
Note: This is a living document that will be continuously updated throughout the project development.

# Audio Processing Pipeline

## Overview

The audio processing pipeline takes meeting recordings and automatically generates ROCKS and tasks. The pipeline consists of several stages:

1. Audio Processing
   - Transcribes audio using Groq's Whisper model
   - Handles large files by chunking
   - Produces clean transcript

2. Semantic Analysis
   - Tokenizes transcript into segments
   - Extracts entities, dates, people, organizations
   - Identifies action items and key phrases

3. ROCKS Generation
   - Analyzes segments in parallel using Gemini
   - Generates structured ROCKS with weekly tasks
   - Validates output format
   - Integrates with employee roles from CSV

4. Database Integration
   - Parses ROCKS and tasks into collection format
   - Associates with quarters and users
   - Maintains data consistency

## API Endpoints

### Upload Endpoints

1. POST `/admin/upload-audio`
   - Upload and process meeting recording
   - Admin only
   - Parameters:
     - `file`: Audio file (mp3, wav, ogg, flac, m4a, webm)
     - `quarter_id`: Optional quarter to associate ROCKS with
   - Background processing
   - Returns upload status and pipeline information

## Environment Variables

- `GEMINI_API_KEY_SCRIPT`: Google Gemini API key
- `GEMINI_MODEL`: Model name (default: gemini-1.5-flash)

## Dependencies

Required packages:
- pydub: Audio processing
- spacy: NLP processing
- google-generativeai: ROCKS generation
- groq: Audio transcription
- demjson3: JSON parsing

## File Structure

```
services/
  pipeline/
    script_pipeline_service.py  - Core pipeline logic
    data_parser_service.py      - Collection data parsing
routes/
  upload.py                     - Upload endpoints
```

## Usage

1. Ensure test.csv exists with employee roles (format: Full Name, Job Role)
2. Upload audio file via API
3. Pipeline runs in background:
   - Transcribes audio
   - Analyzes content
   - Generates ROCKS and tasks
4. Data saved to database if quarter_id provided
5. Access via existing collection endpoints

## Integration Flow

1. Frontend Upload:
   - Send audio file to `/admin/upload-audio`
   - Optionally provide quarter_id

2. Backend Processing:
   - Save audio temporarily
   - Start background pipeline
   - Return immediate response

3. Pipeline Execution:
   - Transcribe audio (Groq Whisper)
   - Semantic analysis (spaCy)
   - ROCKS generation (Gemini)
   - Parse and validate data

4. Database Integration:
   - Create rocks in quarter
   - Create tasks for rocks
   - Link everything properly

5. Cleanup:
   - Remove temporary audio file
   - Log completion status

## Error Handling

- Audio file validation
- Pipeline error tracking
- Database transaction safety
- Background task monitoring
- Proper cleanup on failure

# Audio Processing Pipeline

## Overview

The audio processing pipeline takes meeting recordings and automatically generates ROCKS and tasks. The pipeline consists of several stages:

1. Audio Processing
   - Transcribes audio using Groq's Whisper model
   - Handles large files by chunking
   - Produces clean transcript

2. Semantic Analysis
   - Tokenizes transcript into segments
   - Extracts entities, dates, people, organizations
   - Identifies action items and key phrases

3. ROCKS Generation
   - Analyzes segments in parallel using Gemini
   - Generates structured ROCKS with weekly tasks
   - Validates output format
   - Integrates with employee roles from CSV

4. Database Integration
   - Parses ROCKS and tasks into collection format
   - Associates with quarters and users
   - Maintains data consistency

## API Endpoints

### Upload Endpoints

1. POST `/admin/upload-audio`
   - Upload and process meeting recording
   - Admin only
   - Parameters:
     - `file`: Audio file (mp3, wav, ogg, flac, m4a, webm)
     - `quarter_id`: Optional quarter to associate ROCKS with
   - Background processing
   - Returns upload status and pipeline information

## Environment Variables

- `GEMINI_API_KEY_SCRIPT`: Google Gemini API key
- `GEMINI_MODEL`: Model name (default: gemini-1.5-flash)

## Dependencies

Required packages:
- pydub: Audio processing
- spacy: NLP processing
- google-generativeai: ROCKS generation
- groq: Audio transcription
- demjson3: JSON parsing

## File Structure

```
services/
  pipeline/
    script_pipeline_service.py  - Core pipeline logic
    data_parser_service.py      - Collection data parsing
routes/
  upload.py                     - Upload endpoints
```

## Usage

1. Ensure test.csv exists with employee roles (format: Full Name, Job Role)
2. Upload audio file via API
3. Pipeline runs in background:
   - Transcribes audio
   - Analyzes content
   - Generates ROCKS and tasks
4. Data saved to database if quarter_id provided
5. Access via existing collection endpoints 