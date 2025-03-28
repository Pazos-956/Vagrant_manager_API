from contextlib import asynccontextmanager
from fastapi import FastAPI
from sqlmodel import Field, SQLModel, create_engine

from .routers import vagrant, database

# fastapi dev main.py --host 0.0.0.0
SQLModel.metadata.create_all(database.engine)

app = FastAPI()

app.include_router(database.router)
app.include_router(vagrant.router)


@app.get("/healthcheck")
def checkhealth():
    return {"status": "ok"}
