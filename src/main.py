import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException, status
from sqlmodel import SQLModel, Session
from fastapi.responses import JSONResponse
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

api_key = os.getenv("API_KEY")
if api_key is None:
    raise RuntimeError("La variable de entorno api_key no se ha cargado.")

# @app.exception_handler(HTTPException)
# async def http_exception_handler(request, err):
#     return JSONResponse(status_code=err.status_code,
#                         content={
#                             "status": err.status_code,
#                             "error": err.detail["error"],
#                             "message": err.detail["message"],
#                             "path": request.path_params
#
#                         })

@app.middleware("http")
async def check_token(request: Request, call_next):
    if "X-API-Key" in request.headers:
        token = request.headers["X-API-Key"]
        if token == api_key:
            response = await call_next(request)
            return response
        else:
            raise HTTPException(status_code=403, detail={
                "message": "La API-key es inválida.",
                }
            )
    else:
        return JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                content={"message": "No se ha enviado la API-key."})

app.include_router(vagrant.router)

@app.get("/healthcheck")
def checkhealth():
    return {"status": "ok"}

