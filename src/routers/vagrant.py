from sqlalchemy.exc import StatementError
import vagrant
import os
import shutil
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlmodel import select
from ..dependencies import vagrant_run, load_template, Temp_info
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

    if not os.path.isdir(usr_path):
        raise HTTPException(status_code=404, detail={
            "message": "The user does not exist.",
            "user": usr
            }
        )
    if os.path.isdir(env_path):
        raise HTTPException(status_code=400, detail={
            "message": "The environment already exists.",
            "env": body.env_name
            }
        )
    validate_template_info(body.temp_info)
    
    host = session.exec(select(Host)).first()
    if host == None:
        raise AttributeError("El host está vacio")

    if host.free_cpu >= body.temp_info.cpu and host.free_mem >= body.temp_info.mem and host.free_space >= 10:
        os.mkdir(env_path)
        env = Venv(env_path = env_path, host_id = host.host_id)
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

class Status(BaseModel):
    env_name: str
    machines: list[vagrant.Status] = []

class Global_status(BaseModel):
    status_list: list[Status] = []


@router.get("/{usr}/{env_name}")
def get_status(usr, env_name) -> Status:
    env_path = os.path.normpath(base_path+usr+"/"+env_name)
    usr_path = os.path.normpath(base_path+usr)

    if not os.path.isdir(usr_path):
        raise HTTPException(status_code=404, detail={
            "message": "The user does not exist.",
            "user": usr
            }
        )
    if not os.path.isdir(env_path):
        raise HTTPException(status_code=404, detail={
            "message": "The environment does not exist.",
            "env": env_name
            }
        )

    status = Status(env_name = env_name)
    with vagrant_run(env_path) as v:
        status.machines = v.status()

    return status

@router.get("/{usr}/")
def global_status(usr) -> Global_status:
    usr_path = os.path.normpath(base_path+usr)

    if not os.path.isdir(usr_path):
        raise HTTPException(status_code=404, detail={
            "message": "The user does not exist.",
            "user": usr
            }
        )

    status = Global_status()
    with os.scandir(usr_path) as entries:
        for entry in entries:
            if not entry.is_dir():
                continue
            with vagrant_run(entry) as v:
                env_status = Status(env_name = entry.name)
                env_status.machines = v.status()
                status.status_list.append(env_status)

    return status

@router.delete("/{usr}/{env_name}")
def delete_env(usr, env_name, session: SessionDep):
    env_path = os.path.normpath(base_path+usr+"/"+env_name)
    usr_path = os.path.normpath(base_path+usr)

    if not os.path.isdir(usr_path):
        raise HTTPException(status_code=404, detail={
            "message": "The user does not exist.",
            "user": usr
            }
        )
    if not os.path.isdir(env_path):
        raise HTTPException(status_code=404, detail={
            "message": "The environment does not exist.",
            "env": env_name
            }
        )

    statement = select(Vm, Venv).where(Vm.env_id == Venv.env_id).where(Venv.env_path == env_path)
    result = session.exec(statement).one()
    host = session.exec(select(Host)).first()
    if host == None:
        raise AttributeError("El host está vacio")
    vm = result[0]
    env = result[1]

    with vagrant_run(env_path) as v:
        v.destroy()
    
    host.free_cpu += vm.cpu
    host.free_mem += vm.mem
    host.free_space += vm.space

    session.add(host)
    session.delete(vm)
    shutil.rmtree(env_path)
    session.delete(env)
    session.commit()
    return


    

    





def validate_template_info(temp_info):
    if not temp_info.boxname in boxes:
        raise HTTPException(status_code=404, detail={
            "message": "This box is not allowed.",
            "boxname": temp_info.boxname
            }
        )
    if not temp_info.provider in providers:
        raise HTTPException(status_code=404, detail={
            "message": "This box is not allowed.",
            "provider": temp_info.provider
            }
        )
    if temp_info.cpu < 1:
        raise HTTPException(status_code=404, detail={
            "message": "The cpu must be greater than 1.",
            "cpu": temp_info.cpu
            }
        )
    if temp_info.mem < 1024:
        raise HTTPException(status_code=404, detail={
                "message": "The memory must be greater than 1024.",
                "mem": temp_info.mem
                }
            )







