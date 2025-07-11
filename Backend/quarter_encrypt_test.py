from cryptography.fernet import Fernet
from models.quarter import Quarter
from uuid import uuid4, UUID
from datetime import datetime
import json

# 1. Generate a Fernet key
key = Fernet.generate_key()
fernet = Fernet(key)
print(f"Fernet key: {key.decode()}")

# 2. Create a Quarter instance
quarter = Quarter(
    id=uuid4(),
    quarter="Q2",
    weeks=13,
    year=2024,
    title="Second Quarter Planning",
    description="Planning for Q2 2024",
    participants=[uuid4()],
    status=1,
    created_at=datetime.utcnow(),
    updated_at=datetime.utcnow()
)
print("\nOriginal Quarter instance:")
print(quarter)

# 3. Split UUID and datetime fields from the rest
quarter_dict = quarter.model_dump()
uuid_dt_fields = {
    "id": str(quarter_dict.pop("id")),
    "participants": [str(p) for p in quarter_dict.pop("participants")],
    "created_at": quarter_dict.pop("created_at").isoformat(),
    "updated_at": quarter_dict.pop("updated_at").isoformat()
}
# Now quarter_dict contains only the fields to encrypt

# 4. Serialize and encrypt only the non-UUID, non-datetime data
quarter_json = json.dumps(quarter_dict)
encrypted = fernet.encrypt(quarter_json.encode())
print("\nUUID and datetime fields (plaintext):")
print(uuid_dt_fields)
print("\nEncrypted Quarter (base64):")
print(encrypted.decode())

# 5. Decrypt and reconstruct
decrypted_json = fernet.decrypt(encrypted).decode()
decrypted_data = json.loads(decrypted_json)
# Add UUID and datetime fields back (convert to correct types)
decrypted_data["id"] = UUID(uuid_dt_fields["id"])
decrypted_data["participants"] = [UUID(p) for p in uuid_dt_fields["participants"]]
decrypted_data["created_at"] = datetime.fromisoformat(uuid_dt_fields["created_at"])
decrypted_data["updated_at"] = datetime.fromisoformat(uuid_dt_fields["updated_at"])

quarter_restored = Quarter(**decrypted_data)
print("\nRestored Quarter instance:")
print(quarter_restored) 