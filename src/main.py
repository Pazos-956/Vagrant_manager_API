from contextlib import asynccontextmanager
from fastapi import FastAPI
from sqlmodel import Field, SQLModel, create_engine, Session

from .routers import vagrant, database

# fastapi dev main.py --host 0.0.0.0
SQLModel.metadata.create_all(database.engine)
host = database.Host(
        cpu_total = 3,
        mem_total = 3072,
        space_total = 30,
        free_cpu = 3,
        free_mem = 3072,
        free_space = 30)
with Session(database.engine) as session:
    session.add(host)
    session.commit()

app = FastAPI()

app.include_router(database.router)
app.include_router(vagrant.router)


@app.get("/healthcheck")
def checkhealth():
    return {"status": "ok"}
