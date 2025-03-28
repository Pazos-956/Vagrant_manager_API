import vagrant
import os
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlmodel import select
from ..dependencies import vagrant_run, load_template, Temp_info, log, check_dir
from .database import Vm, Venv, Host, SessionDep

router = APIRouter()

base_path = "/home/vagrant/users/"
boxes = ["ubuntu/jammy64", "generic/rocky8", "opensuse/Leap-15.6.x86_64"]
providers = ["virtualbox", "libvirt", "vmware_desktop"]

# Para validar un objeto para la DB, usar Host.model_validate(host)

class Create_env(BaseModel):
    env_name: str
    temp_info: Temp_info

@router.post("/{usr}/create_env")
def create_env(usr: str, body: Create_env, session: SessionDep):
    body.env_name = os.path.basename(body.env_name) # deletes paths for unwanted subdirectories
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
    
    if not body.temp_info.boxname in boxes:
        raise HTTPException(status_code=404, detail={
            "message": "This box is not allowed.",
            "boxname": body.temp_info.boxname
            }
        )
    if not body.temp_info.provider in providers:
        raise HTTPException(status_code=404, detail={
            "message": "This box is not allowed.",
            "provider": body.temp_info.provider
            }
        )
    if body.temp_info.cpu < 1:
        raise HTTPException(status_code=404, detail={
            "message": "The cpu must be greater than 1.",
            "cpu": body.temp_info.cpu
            }
        )
    if body.temp_info.mem < 1024:
        raise HTTPException(status_code=404, detail={
                "message": "The memory must be greater than 1024.",
                "mem": body.temp_info.mem
                }
            )

    host = session.exec(select(Host)).first()
    if host == None:
        raise AttributeError("El host está vacio")

    if host.free_cpu >= body.temp_info.cpu and host.free_mem >= body.temp_info.mem and host.free_space >= 10:
        os.mkdir(env_path)
        env = Venv(env_name = env_path, host_id = host.host_id)
        session.add(env)
        session.commit()
        load_template(env_path, body.temp_info)
        with vagrant_run(env_path) as v:
            v.up()
    else:
        raise HTTPException(status_code=400, detail={
            "message": "There are not enough resources availables.",
            "cpu": host.free_cpu,
            "mem": host.free_mem,
            "space": host.free_space,
            }
        )
    
    vm = Vm(
            vm_name = body.temp_info.hostname,
            cpu = body.temp_info.cpu,
            mem = body.temp_info.mem,
            space = 7,
            env_id = env.env_id
            )
    session.add(vm)

    host.free_cpu -= vm.cpu
    host.free_mem -= vm.mem
    host.free_space -= vm.space
    session.add(host)
    session.commit()
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











