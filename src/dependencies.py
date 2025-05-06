import contextlib
import vagrant
import os
import shutil
import psutil
import time
import logging
from sqlmodel import select
from .database.database import Vm, Venv, Host, get_session
from fastapi import HTTPException, status

log_file = os.getenv("LOG_FILE")

print("Esto es dependencies:  ")
print(os.getcwd())
print("\n")

log = logging.getLogger(__name__)
logging.basicConfig(
        format="%(asctime)s - %(levelname)s: %(message)s",
        filename=log_file, encoding="utf-8", level=logging.INFO)

log_cm = vagrant.make_file_cm(log_file)

@contextlib.contextmanager
def vagrant_run(path):
    abspath = os.path.abspath(path)
    v = vagrant.Vagrant(
            root=abspath,  #confirmar que el abspath existe antes, si no existe no hace nada
            # Tampoco manda ninguna clase de error.
            err_cm=vagrant.stderr_cm,
            out_cm=vagrant.stdout_cm
            )
    try:
        yield v
    except Exception as err:
        pid = None
        for proc in psutil.process_iter(["name", "pid"]):
            if proc.info["name"] == "vagrant":
                pid = proc.info["pid"]
        while pid != None:
            if psutil.pid_exists(pid):
                time.sleep(3)
            else:
                pid = None
        if "up" in err.args[1] and (len(err.args[1]) == 3):
            
            v.destroy()
            shutil.rmtree(path)
            with get_session() as session:
                statement = select(Vm, Venv).where(Vm.env_id == Venv.env_id).where(Venv.env_path == path)
                result = session.exec(statement).one()
                host = session.exec(select(Host)).first()
                if host == None:
                    raise AttributeError("El host está vacio")
                vm = result[0]
                env = result[1]

                host.free_cpu += vm.cpu
                host.free_mem += vm.mem
                host.free_space += vm.space

                session.add(host)
                session.delete(vm)
                session.delete(env)
                session.commit()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail={
            "message": "Ha ocurrido un error en Vagrant.",
            #"message": f"El comando 'vagrant {err.args[1][1]} {err.args[1][2]}' ha devuelto un estado de salida {err.args[0]}.",
                }
        )

class Response():
    hostName: str
    user: str
    port: int

def parse_response(conf):
    response = Response()
    response.hostName = conf["HostName"]
    response.port = conf["Port"]


