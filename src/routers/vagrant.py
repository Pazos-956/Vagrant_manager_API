import vagrant
import os
import shutil
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlmodel import select
from jinja2 import Environment, FileSystemLoader
from ..dependencies import vagrant_run
from .database import Vm, Venv, Host, SessionDep

router = APIRouter()

base_path = os.getenv("USERS_PATH")
if base_path is None:
    raise RuntimeError("La variable de entorno USERS_PATH no se ha cargado.")

temp_dir = os.getenv("TEMP_DIR")
if temp_dir is None:
    raise RuntimeError("La variable de entorno TEMP_DIR no se ha cargado.")

boxes = {
        "ubuntu/jammy64": {"providers": ["virtualbox"], "space": 40},
        "hashicorp/precise64": {"providers": ["virtualbox", "libvirt", "vmware_desktop"], "space": 80},
        "centos/7": {"providers": ["virtualbox", "libvirt", "vmware_desktop"], "space": 40}
        }

class Vagr_info(BaseModel):
    cpu: int = 1
    mem: int = 1024
    boxname: str = "ubuntu/jammy64"
    hostname: str 
    provider: str = "virtualbox"

class Create_env(BaseModel):
    env_name: str
    vagr_info: Vagr_info

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
    validate_vagrant_info(body.vagr_info)
    
    host = session.exec(select(Host)).first()
    if host == None:
        raise AttributeError("El host está vacio")

    if (host.free_cpu >= body.vagr_info.cpu
        and host.free_mem >= body.vagr_info.mem
        and host.free_space >= boxes[body.vagr_info.boxname]["space"]):
        os.mkdir(env_path)
        load_template(env_path, body.vagr_info)
        with vagrant_run(env_path) as v:
            v.up(provider=body.vagr_info.provider)
            env = Venv(env_path = env_path, host_id = host.host_id)
        session.add(env)
        session.commit()
    else:
        raise HTTPException(status_code=400, detail={
            "message": "There are not enough resources availables.",
            "cpu": host.free_cpu,
            "mem": host.free_mem,
            "space": host.free_space,
            }
        )
    
    vm = Vm(
            vm_name = body.vagr_info.hostname,
            cpu = body.vagr_info.cpu,
            mem = body.vagr_info.mem,
            space = boxes[body.vagr_info.boxname]["space"],
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

@router.put("/{usr}/{env_name}/up")
def vagrant_up(usr, env_name):
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

    with vagrant_run(env_path) as v:
        v.up()
    return

    
@router.put("/{usr}/{env_name}/halt")
def vagrant_halt(usr, env_name):
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

    with vagrant_run(env_path) as v:
        v.halt()
    return

def validate_vagrant_info(vagr_info):
    if not vagr_info.boxname in boxes:
        raise HTTPException(status_code=404, detail={
            "message": "This box is not allowed.",
            "boxname": vagr_info.boxname
            }
        )
    if not vagr_info.provider in boxes[vagr_info.boxname]["providers"]:
        raise HTTPException(status_code=404, detail={
            "message": "This box is not allowed.",
            "provider": vagr_info.provider
            }
        )
    if vagr_info.cpu < 1:
        raise HTTPException(status_code=404, detail={
            "message": "The cpu must be greater than 1.",
            "cpu": vagr_info.cpu
            }
        )
    if vagr_info.mem < 1024:
        raise HTTPException(status_code=404, detail={
                "message": "The memory must be greater than 1024.",
                "mem": vagr_info.mem
                }
        )

def load_template(path, temp_info):
    env = Environment(loader=FileSystemLoader(temp_dir))
    template = env.get_template("vagrantfile.template")
    contenido = template.render(temp_info)

    vfile = os.path.abspath(path+"/Vagrantfile")
    with open(vfile, "w") as file:
        file.write(contenido)
