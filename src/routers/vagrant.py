import vagrant
import os
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from ..dependencies import vagrant_run, load_template, Temp_info, log, check_dir
from .database import Vm, Venv, Host, SessionDep

router = APIRouter()

base_path = "/home/vagrant/users/"

# Para validar un objeto para la DB, usar Host.model_validate(host)

class Create_env(BaseModel):
    env_name: str
    temp_info: Temp_info

@router.post("/{usr}/create_env")
def create_env(usr: str, body: Create_env, session: SessionDep):
    env_path = os.path.normpath(base_path+usr+"/"+body.env_name)
    usr_path = os.path.normpath(base_path+usr)

    if not check_dir(usr_path):
        raise HTTPException(status_code=404, detail={
            "message": "The user does not exist.",
            "user": usr
            }
        )
    if check_dir(env_path):
        raise HTTPException(status_code=400, detail={
            "message": "The environment already exists.",
            "env": body.env_name
            }
        )
    # Ver una forma de que no puedas pasarle subdirectorios IMPORTANTE !!!!
    os.mkdir(env_path)

    with vagrant_run(env_path) as v:
        load_template(body.temp_info)
        v.up()
    return body

class Dir(BaseModel):
    dirname: str
    machines: list[vagrant.Status] = []

class Status(BaseModel):
    dirs: list[Dir] = []


@router.get("/{usr}/status")
def get_status(usr, dirname: str | None = None) -> Status:
    status = Status(dirs=[])
    if dirname == None:
        with os.scandir("/vagrant/"+usr) as entries:
            for entry in entries:
                if entry.is_dir():
                    with vagrant_run(entry) as v:
                        result = v.status()
                        dire = Dir(dirname="", machines=[])
                        dire.dirname = entry.name
                        dire.machines = result
                        status.dirs.append(dire)
    else:
        entry = "/vagrant/"+usr+"/"+dirname
        if os.path.isdir(entry):
            with vagrant_run(entry) as v:
                result = v.status()
                dire = Dir(dirname="", machines=[])
                dire.dirname = dirname
                dire.machines = result
                status.dirs.append(dire)
    return status











