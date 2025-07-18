# Employee Status Toggle UI Guide

## Overview
This document describes the status toggle functionality for employees in the Commetrix application. Employees can update the status of todos, issues, and milestones assigned to them through large, obvious UI buttons.

## Features Implemented

### 1. Todo Status Updates
- **Endpoint**: `PUT /todos/{todo_id}/status`
- **Frontend**: Large colored toggle buttons in TaskListCard.jsx
- **Access**: Employees can update todos assigned to them
- **Status Flow**: pending ↔ completed

### 2. Issue Status Updates
- **Endpoint**: `PUT /issues/{issue_id}/status`
- **Frontend**: Large colored toggle buttons in TaskListCard.jsx
- **Access**: Employees can update issues assigned to them
- **Status Flow**: open ↔ resolved

### 3. Milestone Status Updates (NEW)
- **Endpoint**: `PUT /tasks/{task_id}/status`
- **Frontend**: Large colored toggle buttons in RocksCard.jsx
- **Access**: Employees can update milestones for rocks assigned to them
- **Status Flow**: pending ↔ completed

## Backend Implementation

### Task Model Updates
Added status fields to the Task model:
```python
completed: Optional[bool] = Field(default=False, description="Whether the task/milestone is completed")
status: Optional[str] = Field(default="pending", description="Task/milestone status (pending, completed, done, etc.)")
```

### Milestone Status Endpoint
```python
@router.put("/tasks/{task_id}/status", response_model=Task)
async def update_milestone_status(
    task_id: UUID,
    status_data: dict,
    current_user: User = Depends(get_current_user)
) -> Task:
```

**Access Control**:
- Facilitator users can update any milestone
- Employees can only update milestones for rocks assigned to them

**Request Body**:
```json
{
  "status": "completed"  // or "pending"
}
```

## Frontend Implementation

### API Service
Added mutation in `services/api.js`:
```javascript
updateMilestoneStatus: builder.mutation({
    query: ({ task_id, status, token }) => ({
        url: `/tasks/${task_id}/status`,
        method: 'PUT',
        body: { status },
        headers: token ? { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' } : { 'Content-Type': 'application/json' },
    }),
}),
```

### MeetingSummary Integration
Updated `handleStatusUpdate` to handle milestones:
```javascript
else if (entityType === 'milestone') {
    result = await updateMilestoneStatus({ task_id: entityId, status: newStatus, token });
}
```

### RocksCard Component
- Added `handleMilestoneStatusClick` function
- Implemented large, colored status toggle buttons
- Added permission checking (`canUpdateMilestoneStatus`)

## UI Design

### Button Styling
All status buttons use consistent styling:
- **Large size**: 120px width, 40px height
- **Color coding**:
  - Completed: Green background (#10b981)
  - Pending: Yellow/orange background (#f59e0b)
- **Hover effects**: Slightly darker shade
- **Click feedback**: Console logging for debugging
- **Tooltips**: Clear instructions for users

### Button Text
- Completed: "✅ Completed"
- Pending: "⏳ Pending"

## Testing Mode

**TEMPORARY TESTING MODE ENABLED**: All users can currently see and click status buttons for easier testing and debugging. This bypasses normal role/assignment checks.

To disable testing mode:
1. Remove the temporary override in `canUpdateStatus` functions
2. Restore original role-based permission checks

## Access Control

### Normal Operation (when testing mode is disabled)
- **Facilitators**: Cannot update status (view-only for Facilitator interface)
- **Employees**: Can only update entities assigned to them
- **Permission checks**: Based on rock assignment, todo assignment, issue assignment

### Current Testing Mode
- All authenticated users can update any status
- Useful for development and debugging
- Should be disabled in production

## Error Handling

### Frontend
- Loading spinners during API calls
- Error alerts for failed requests
- Console logging for debugging
- Network error detection

### Backend
- Proper HTTP status codes
- Detailed error messages
- Permission validation
- Entity existence checks

## Debug Features

### Console Logging
Extensive logging throughout the status update flow:
- Button clicks
- Permission checks
- API calls
- Status changes
- Error conditions

### Network Monitoring
- Check browser developer tools Network tab
- Monitor API requests/responses
- Verify endpoint calls and status codes

## Data Flow

1. **User clicks status button** → `handleMilestoneStatusClick`
2. **Permission check** → `canUpdateMilestoneStatus`
3. **Status calculation** → Toggle current status
4. **API call** → `onStatusUpdate` → `handleStatusUpdate`
5. **Backend update** → Update database
6. **UI refresh** → Refetch data and update display

## Known Issues and Solutions

### Issue: 404 Errors
- **Cause**: Missing backend endpoints
- **Solution**: Verify all endpoints exist and are properly implemented

### Issue: Status not updating
- **Cause**: Permission restrictions or API failures
- **Solution**: Check console logs, verify user assignments

### Issue: Buttons not clickable
- **Cause**: CSS z-index or event propagation issues
- **Solution**: Use large, obvious buttons with proper click handling

## Future Enhancements

1. **Real-time updates**: WebSocket integration for live status updates
2. **Batch operations**: Multiple status updates at once
3. **Status history**: Track who changed status when
4. **Custom statuses**: Allow more than just pending/completed
5. **Notifications**: Notify team members of status changes

## Testing Checklist

- [ ] Backend endpoints respond correctly
- [ ] Frontend API calls succeed
- [ ] Status buttons are visible and clickable
- [ ] Permission checks work correctly
- [ ] UI updates after status changes
- [ ] Error handling works for network issues
- [ ] Console logs provide helpful debugging info
- [ ] Testing mode can be easily disabled

## Production Deployment

Before deploying to production:
1. **Disable testing mode** in all components
2. **Verify permission checks** are working correctly
3. **Test with real user assignments**
4. **Monitor for errors** in production logs
5. **Ensure proper CORS configuration**
