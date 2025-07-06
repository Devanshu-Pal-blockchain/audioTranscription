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

### Backend Structure
- Focus on routes/ and service/ directories
- Clean separation of concerns
- No LLM/RAG/Langchain dependencies (removed from scope)
- New `models/` directory for schema definitions

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
  participants: UUID[]      // Array of participant IDs
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

---
Last Updated: [Current Date]
Note: This is a living document that will be continuously updated throughout the project development. 