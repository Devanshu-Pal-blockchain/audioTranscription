
from fastapi import FastAPI

from routes import auth
from routes import register

app = FastAPI()



app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(register.router, prefix="/auth", tags=["register"])

@app.get("/")
def read_root():
    return {"message": "FastAPI backend is running!"}
