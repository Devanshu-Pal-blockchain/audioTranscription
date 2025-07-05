
from fastapi import FastAPI


from routes import auth
from routes import register
from routes import upload_csv
from routes import upload_audio
from routes import rag

app = FastAPI()





app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(register.router, prefix="/auth", tags=["register"])
app.include_router(upload_csv.router, prefix="/admin", tags=["admin-csv"])
app.include_router(upload_audio.router, prefix="/admin", tags=["admin-audio"])
app.include_router(rag.router, prefix="/rag", tags=["rag-mcp"])

@app.get("/")
def read_root():
    return {"message": "FastAPI backend is running!"}
