import json
import uuid

QUARTER_ID = "3c1ac356-3ffb-4c5a-8ecc-27c5365735ff"

# Read the rocks and tasks data
with open('rocks.json', 'r') as f:
    rocks = json.load(f)

with open('tasks.json', 'r') as f:
    tasks = json.load(f)

# Assign UUIDs to rocks and add quarter_id
rock_mapping = {}  # To store rock_name to rock_id mapping
formatted_rocks = []

for rock in rocks:
    rock_id = str(uuid.uuid4())
    rock_mapping[rock['rock_name']] = rock_id
    
    formatted_rock = {
        **rock,
        'rock_id': rock_id,
        'quarter_id': QUARTER_ID
    }
    formatted_rocks.append(formatted_rock)

# Group tasks by their corresponding rocks based on the task content
tasks_by_rock = {rock_id: [] for rock_id in rock_mapping.values()}

# Helper function to determine which rock a task belongs to based on context
def determine_rock_for_task(task_content, rocks_data):
    # MarTech Migration tasks
    if any(keyword in task_content.lower() for keyword in ['hubspot', 'customer.io', 'webhook', 'email', 'marketing automation']):
        return next(rock['rock_id'] for rock in rocks_data if 'MarTech Migration' in rock['rock_name'])
    
    # Investor Deck tasks
    if any(keyword in task_content.lower() for keyword in ['investor', 'deck', 'metrics', 'revenue', 'testimonials']):
        return next(rock['rock_id'] for rock in rocks_data if 'Investor Deck' in rock['rock_name'])
    
    # Customer Advisory Board tasks
    if any(keyword in task_content.lower() for keyword in ['advisory', 'cab', 'customer', 'power users', 'feedback']):
        return next(rock['rock_id'] for rock in rocks_data if 'Customer Advisory Board' in rock['rock_name'])
    
    # Notion tasks
    if any(keyword in task_content.lower() for keyword in ['notion', 'workspace', 'archiving', 'tagline']):
        return next(rock['rock_id'] for rock in rocks_data if 'Streamline Notion' in rock['rock_name'])
    
    return None

# Assign tasks to rocks and format them
for task in tasks:
    task_id = str(uuid.uuid4())
    rock_id = determine_rock_for_task(task['task'], formatted_rocks)
    
    if rock_id:
        formatted_task = {
            **task,
            'task_id': task_id,
            'rock_id': rock_id
        }
        tasks_by_rock[rock_id].append(formatted_task)

# Create the final payload
payload = {
    'rocks': formatted_rocks,
    'tasks_by_rock': tasks_by_rock
}

# Save the formatted data
with open('formatted_bulk_data.json', 'w') as f:
    json.dump(payload, f, indent=2)

print("Data formatted successfully and saved to formatted_bulk_data.json")
print(f"Total rocks: {len(formatted_rocks)}")
print(f"Tasks distribution:")
for rock in formatted_rocks:
    print(f"- {rock['rock_name']}: {len(tasks_by_rock[rock['rock_id']])} tasks") 