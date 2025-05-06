import os
import datetime
from time import time
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException, status
from sqlmodel import SQLModel, Session
from fastapi.responses import JSONResponse
from dotenv import load_dotenv

load_dotenv()
from .routers import vagrant, users
from .database import database

api_key = os.getenv("API_KEY")
log_file = os.getenv("LOG_FILE")
DB = os.getenv("DATABASE")

if api_key is None:
    raise RuntimeError("La variable de entorno api_key no se ha cargado.")
if log_file is None:
    raise RuntimeError("La variable de entorno LOG_FILE no se ha cargado.")
if DB is None:
    raise RuntimeError("La variable de entorno DATABASE no se ha cargado.")
if os.getenv("TMPL_DIR") is None:
    raise RuntimeError("La variable de entorno TMPL_DIR no se ha cargado.")
if os.getenv("USERS_PATH") is None:
    raise RuntimeError("La variable de entorno api_key no se ha cargado.")


auth_ips = ["127.0.0.1","192.168.1.131"]
request_counts = {}
RATE_LIMIT = 10
TIME_WINDOW = 60

app = FastAPI()

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
    with database.get_session() as session:
        session.add(host)
        session.commit()


@app.exception_handler(HTTPException)
async def http_exception_handler(request, err):
    return JSONResponse(status_code=err.status_code,
                        content={
                            "status": err.status_code,
                            "path": request.url.path,
                            "datetime": datetime.datetime.now().strftime("%x %X.%f"),
                            "details": err.detail
                            
                        })

@app.middleware("http")
async def request_limit_middleware(request: Request, call_next):
    assert request.client is not None

    if request.client.host not in request_counts:
        request_counts.update({request.client.host:(time(), 1)})
    else:
        timestamp, count = request_counts[request.client.host]

        if (time() - timestamp) > TIME_WINDOW:
            count = 0
            timestamp = time()

        count +=1
        if count > RATE_LIMIT:
            time_left = TIME_WINDOW-(time()-timestamp)
            return JSONResponse(status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                                content={
                                    "status": status.HTTP_429_TOO_MANY_REQUESTS,
                                    "path": request.url.path,
                                    "datetime": datetime.datetime.now().strftime("%x %X.%f"),
                                    "details": {
                                        "message": f"Se ha excedido el número de peticiones permitidas, inténtelo en {round(time_left,2)} segundos.",
                                    }
                                    })

        request_counts.update({request.client.host:(timestamp,count)})

    response = await call_next(request)
    return response

@app.middleware("http")
async def check_authorization(request: Request, call_next):
    assert request.client is not None
    if request.client.host not in auth_ips:
            return JSONResponse(status_code=status.HTTP_403_FORBIDDEN,
                content={
                    "status": status.HTTP_403_FORBIDDEN,
                    "path": request.url.path,
                    "datetime": datetime.datetime.now().strftime("%x %X.%f"),
                    "details": {
                        "message": "Su IP no está autorizada para realizar peticiones a la API.",
                        "ip": request.client.host
                    }
            })
    if "X-API-Key" in request.headers:
        token = request.headers["X-API-Key"]
        if token == api_key:
            response = await call_next(request)
            return response
        else:
            return JSONResponse(status_code=status.HTTP_403_FORBIDDEN,
                content={
                    "status": status.HTTP_403_FORBIDDEN,
                    "path": request.url.path,
                    "datetime": datetime.datetime.now().strftime("%x %X.%f"),
                    "details":{
                        "message": "La API-key proporcionada es inválida.",
                    }
            })
    else:
        return JSONResponse(status_code=status.HTTP_403_FORBIDDEN,
            content={
                "status": status.HTTP_403_FORBIDDEN,
                "path": request.url.path,
                "datetime": datetime.datetime.now().strftime("%x %X.%f"),
                "details":{
                    "message": "No se ha proporcionado la API-key, añada la cabecera X-API-Key.",
                }
        })


app.include_router(vagrant.router)
app.include_router(users.router)

