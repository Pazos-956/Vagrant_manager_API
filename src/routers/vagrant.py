from starlette.status import HTTP_204_NO_CONTENT
import vagrant
import os
import shutil
from fastapi import APIRouter, HTTPException, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlmodel import select
from jinja2 import Environment, FileSystemLoader, select_autoescape
from ..dependencies import vagrant_run
from ..database.database import Vm, Venv, Host, SessionDep

router = APIRouter()

users_path = os.getenv("USERS_PATH")
tmpl_dir = os.getenv("TMPL_DIR")

boxes = {
        "ubuntu/jammy64": {"providers": ["virtualbox"], "space": 40},
        "hashicorp/precise64": {"providers": ["virtualbox", "libvirt", "vmware_desktop"], "space": 80},
        "centos/7": {"providers": ["virtualbox", "libvirt", "vmware_desktop"], "space": 40}
        }

class Vagr_info(BaseModel):
    env_name: str
    cpu: int = 1
    mem: int = 1024
    boxname: str = "ubuntu/jammy64"
    hostname: str 
    provider: str = "virtualbox"

@router.post("/{usr}/create_env", status_code=status.HTTP_201_CREATED)
def create_env(usr: str, body: Vagr_info, session: SessionDep):
    assert users_path
    body.env_name = os.path.basename(body.env_name) # deletes paths for unwanted subdirectories
    env_path = os.path.normpath(users_path+usr+"/"+body.env_name)
    usr_path = os.path.normpath(users_path+usr)
    response: Response

    if not os.path.isdir(usr_path):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={
            "message": "No se ha encontrado el usuario.",
            "user": usr
            }
        )
    if os.path.isdir(env_path):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail={
            "message": "El entorno ya existe.",
            "env": body.env_name
            }
        )
    validate_vagrant_info(body)
    
    host = session.exec(select(Host)).first()
    if host == None:
        raise AttributeError("El host está vacio")

    if (host.free_cpu >= body.cpu
        and host.free_mem >= body.mem
        and host.free_space >= boxes[body.boxname]["space"]):
        os.mkdir(env_path)
        load_template(env_path, body)
        env = Venv(env_path = env_path, host_id = host.host_id)
        session.add(env)
        session.commit()

        vm = Vm(
                vm_name = body.hostname,
                cpu = body.cpu,
                mem = body.mem,
                space = boxes[body.boxname]["space"],
                env_id = env.env_id
                )
        session.add(vm)
        host.free_cpu -= vm.cpu
        host.free_mem -= vm.mem
        host.free_space -= vm.space
        session.add(host)
        session.commit()
        
        open(env_path+"/script.sh",'a').close()
        with vagrant_run(env_path) as v:
            v.up(provider=body.provider)
            response = create_response(v.conf(), env_path)
    
    else:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail={
            "message": "No hay suficientes recursos disponibles",
            "cpu": host.free_cpu,
            "mem": host.free_mem,
            "space": host.free_space,
            }
        )
    return response

class State(BaseModel):
    env_name: str
    machines: list[vagrant.Status] = []

class Global_state(BaseModel):
    state_list: list[State] = []

@router.get("/{usr}/global_state")
def get_global_state(usr) -> Global_state:
    usr_path = os.path.normpath(users_path+usr)

    if not os.path.isdir(usr_path):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={
            "message": "No se ha encontrado el usuario.",
            "user": usr
            }
        )

    global_state = Global_state()
    with os.scandir(usr_path) as entries:
        for entry in entries:
            if not entry.is_dir():
                continue
            with vagrant_run(entry) as v:
                env_state = State(env_name = entry.name)
                env_state.machines = v.status()
                global_state.state_list.append(env_state)

    return global_state

@router.get("/{usr}/{env_name}")
def get_state(usr, env_name) -> State:
    _, env_path = validate_new_route(usr, env_name)

    state = State(env_name = env_name)
    with vagrant_run(env_path) as v:
        state.machines = v.status()

    return state

@router.delete("/{usr}/{env_name}", status_code=status.HTTP_204_NO_CONTENT)
def delete_env(usr, env_name, session: SessionDep):
    _, env_path = validate_new_route(usr, env_name)

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
    _, env_path = validate_new_route(usr, env_name)
    response: Response

    with vagrant_run(env_path) as v:
        v.up()
        response = create_response(v.conf(), env_path)
    return response

    
@router.put("/{usr}/{env_name}/halt", status_code=status.HTTP_204_NO_CONTENT)
def vagrant_halt(usr, env_name):
    _, env_path = validate_new_route(usr, env_name)

    with vagrant_run(env_path) as v:
        v.halt()
    return

@router.put("/{usr}/{env_name}/suspend", status_code=status.HTTP_204_NO_CONTENT)
def vagrant_suspend(usr, env_name):
    _, env_path = validate_new_route(usr, env_name)

    with vagrant_run(env_path) as v:
        v.suspend()
    return

@router.get("/{usr}/{env_name}/connection_info")
def vagrant_conn_info(usr, env_name):
    _, env_path = validate_new_route(usr, env_name)
    response: Response

    with vagrant_run(env_path) as v:
        response = create_response(v.conf(), env_path)
    return response

@router.put("/{usr}/{env_name}/provision", status_code=status.HTTP_204_NO_CONTENT)
def vagrant_provision(usr, env_name):
    _, env_path = validate_new_route(usr, env_name)

    with vagrant_run(env_path) as v:
        v.provision(provision_with=["optional"])

    return

def validate_new_route(usr, env_name):
    env_path = os.path.normpath(users_path+usr+"/"+env_name)
    usr_path = os.path.normpath(users_path+usr)

    if not os.path.isdir(usr_path):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={
            "message": "No se ha encontrado el usuario.",
            "user": usr
            }
        )
    if not os.path.isdir(env_path):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={
            "message": "No se ha encontrado el entorno.",
            "env": env_name
            }
        )
    return usr_path, env_path

def validate_vagrant_info(vagr_info):
    if not vagr_info.boxname in boxes:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail={
            "message": "El valor 'boxname' introducido no es válido.",
            "invalid_boxname": vagr_info.boxname,
            "available_boxnames": [ "ubunt/jammy64","hashicorp/precise64", "centos/7"]
            })
    if not vagr_info.provider in boxes[vagr_info.boxname]["providers"]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail={
            "message": "El provider introducido no es válido para esta máquina.",
            "invalid_provider": vagr_info.provider,
            "available_providers": boxes[vagr_info.boxname]["providers"]
            })
    if vagr_info.cpu < 1:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail={
            "message": "El valor de CPU introducido debe ser mayor que 1.",
            "cpu": vagr_info.cpu
            })
    if vagr_info.mem < 1024:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail={
                "message": "El valor de memoria introducido deve ser mayor que 1024.",
                "mem": vagr_info.mem
                })


def load_template(path, body):
    assert tmpl_dir
    env = Environment(loader=FileSystemLoader(tmpl_dir))
    template = env.get_template("vagrantfile.template")
    contenido = template.render(body)

    vfile = os.path.abspath(path+"/Vagrantfile")
    with open(vfile, "w") as file:
        file.write(contenido)

class Response():
    hostName: str
    user: str
    port: int

def create_response(conf, env_path):
    response = Response()
    provider = ""

    with open(env_path+"/Vagrantfile") as vf:
        for row in vf.readlines():
            if row.find("libvirt") != -1:
                provider = "libvirt"
                break
            if row.find("virtualbox") != -1:
                provider = "virtualbox"
                break
            if row.find("vmware_desktop") != -1:
                provider = "vmware_desktop"
                break
                
    response.user = conf["Host"]
    response.port = conf["Port"]

    if provider == "libvirt":
        response.port = 2222

    ip = os.popen('ip addr show enp2s0 | grep "inet " | awk \'{ print $2 }\' | awk -F "/" \'{print $1}\'').read().strip()
    response.hostName = ip


    return response


