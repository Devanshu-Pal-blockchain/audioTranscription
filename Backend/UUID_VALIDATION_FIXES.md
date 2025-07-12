# UUID Validation Fixes for Participant Assignment

## Problem Description

The application was encountering `ValidationError` when trying to create Rock, Todo, and Issue models due to empty string values being passed for UUID fields (specifically `assigned_to_id`, `raised_by_id`). The error message was:

```
pydantic_core._pydantic_core.ValidationError: 1 validation error for Rock
assigned_to_id
  Input should be a valid UUID, invalid length: expected length 32 for simple format, found 0 [type=uuid_parsing, input_value='', input_type=str]
```

This occurred when:
1. Frontend sends participant data but some names don't have corresponding IDs in the system
2. The LLM generates names that don't exist in the participants list
3. Database contains legacy data with empty string UUIDs instead of NULL values

## Root Causes

1. **Model Definition Issue**: The `assigned_to_id` field in Rock model was defined as required `UUID` instead of `Optional[UUID]`
2. **Data Parsing Issue**: The data parser service was setting `assigned_to_id` to empty strings instead of `None` for unmatched participants
3. **Database Serialization Issue**: The `secure_fields.py` was keeping empty strings instead of converting them to `None`
4. **Service Layer Issue**: The `safe_decrypt_dict` methods in services weren't handling empty string UUIDs

## Fixes Applied

### 1. Model Definition Updates

**File: `models/rock.py`**
```python
# BEFORE
assigned_to_id: UUID = Field(description="ID of the assigned user")
assigned_to_name: str = Field(description="Name of the assigned user")

# AFTER
assigned_to_id: Optional[UUID] = Field(default=None, description="ID of the assigned user (None if unassigned)")
assigned_to_name: str = Field(default="", description="Name of the assigned user")
```

### 2. Enhanced Participant Validation

**File: `service/data_parser_service.py`**

Added comprehensive participant validation with multiple strategies:

```python
def validate_and_map_participant(self, name: str, participants: Optional[List] = None) -> Tuple[Optional[str], str]:
    """
    Validate and map participant name to ID with comprehensive fallback strategies.
    
    Strategies:
    1. Exact match (case-insensitive)
    2. Fuzzy matching for close names (cutoff=0.8)
    3. Partial name matching (first/last name)
    """
```

**Key Features:**
- **Exact Matching**: Case-insensitive exact name matching
- **Fuzzy Matching**: Uses `difflib.get_close_matches` with 80% similarity threshold
- **Partial Matching**: Matches individual name parts for incomplete names
- **Comprehensive Logging**: Detailed logs for debugging participant matching
- **Safe Fallbacks**: Creates "UNASSIGNED: Original Name" when no match found

### 3. UUID Field Sanitization

**File: `utils/secure_fields.py`**
```python
# BEFORE
else:
    # Keep empty strings or other types as-is
    result[k] = v

# AFTER
else:
    # Convert empty strings or other invalid values to None
    result[k] = None
```

### 4. Service Layer UUID Cleanup

Updated all service `safe_decrypt_dict` methods to handle empty string UUIDs:

**Files: `service/rock_service.py`, `service/todo_service.py`, `service/issue_service.py`, `service/task_service.py`**

```python
# Clean up UUID fields - convert empty strings to None
uuid_fields = ["id", "rock_id", "assigned_to_id", "quarter_id"]
for field in uuid_fields:
    if field in data and data[field] == "":
        data[field] = None
```

### 5. Enhanced Prompt Validation

**File: `service/script_pipeline_service.py`**

Added explicit participant validation rules in the LLM prompt:

```python
## CRITICAL PARTICIPANT VALIDATION RULES

**MANDATORY**: You MUST ONLY assign tasks, todos, issues, and rocks to participants who appear in the official participants list below.

**OFFICIAL PARTICIPANTS LIST:**
{roles_str}

**VALIDATION REQUIREMENTS:**
- For "rock_owner", "assigned_to", "raised_by" fields: Use EXACT full names from the participants list above
- If a person mentioned in the meeting is NOT in the participants list, DO NOT assign any work to them
- If assignment is unclear, leave the rock/task/todo UNASSIGNED rather than guessing
- Use "UNASSIGNED" as the value if no clear participant match exists
```

## Data Flow Improvements

### Before Fixes
```
Frontend → Pipeline → Parser → Database
    ↓           ↓        ↓        ↓
Participant → LLM → Empty String → ValidationError
   Names    Response   UUID         ❌
```

### After Fixes
```
Frontend → Pipeline → Enhanced Parser → Database
    ↓        ↓              ↓            ↓
Participant → LLM → Validation Logic → Clean Data
   Names    Response   + Fallbacks      ✅
                           ↓
                      None for unmatched
                      Valid UUID for matched
                      "UNASSIGNED: Name" prefix
```

## Benefits

1. **Robust Participant Matching**: Multiple fallback strategies ensure maximum matching success
2. **Clear Assignment Tracking**: Unmatched participants are clearly marked as "UNASSIGNED: Original Name"
3. **Database Integrity**: No more empty string UUIDs causing validation errors
4. **Comprehensive Logging**: Detailed logs for debugging participant assignment issues
5. **Backward Compatibility**: Handles existing database records with empty string UUIDs
6. **LLM Prompt Clarity**: Explicit instructions reduce invalid assignments from LLM

## Testing

Created comprehensive test suite in `test_uuid_fixes.py` that validates:
- Rock model accepts None for assigned_to_id
- Service layer properly cleans empty string UUIDs
- Todo and Issue models handle None IDs correctly
- Complete participant validation workflow

## Usage Examples

### Valid Assignment (Match Found)
```python
# Input from LLM
rock_owner = "Alice Johnson"

# Available participants
participants = [
    {"employee_id": "123e4567-...", "employee_name": "Alice Johnson", ...}
]

# Result
assigned_to_id = "123e4567-..."
assigned_to_name = "Alice Johnson"
```

### Invalid Assignment (No Match)
```python
# Input from LLM
rock_owner = "Unknown Person"

# Result
assigned_to_id = None
assigned_to_name = "UNASSIGNED: Unknown Person"
```

### Fuzzy Match
```python
# Input from LLM
rock_owner = "alice johnson"  # lowercase

# Result (case-insensitive match)
assigned_to_id = "123e4567-..."
assigned_to_name = "Alice Johnson"
```

## Migration Notes

- **Existing Data**: The fixes handle existing database records with empty string UUIDs
- **API Compatibility**: All existing API endpoints continue to work
- **Frontend Impact**: No changes required to frontend - it continues sending participant lists as before
- **Database Schema**: No schema changes required - fields already support NULL values

## Monitoring

The enhanced logging provides visibility into:
- Participant matching success/failure rates
- Common mismatched names for manual review
- Database UUID cleanup operations
- Rock assignment patterns

This ensures ongoing visibility into the participant assignment process and helps identify any future issues.
