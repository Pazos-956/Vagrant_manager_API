import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from sqlmodel import SQLModel, Session
from .routers import vagrant
from .database import database


DB = os.getenv("DATABASE")
if DB is None:
    raise RuntimeError("La variable de entorno DATABASE no se ha cargado.")

# fastapi dev main.py --host 0.0.0.0
if not os.path.exists(DB):
    SQLModel.metadata.create_all(database.engine)
    host = database.Host(
            cpu_total = 3,
            mem_total = 3072,
            space_total = 110,
            free_cpu = 3,
            free_mem = 3072,
            free_space = 110)
    with Session(database.engine) as session:
        session.add(host)
        session.commit()

app = FastAPI()

app.include_router(vagrant.router)


@app.get("/healthcheck")
def checkhealth():
    return {"status": "ok"}

