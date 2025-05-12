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

log = logging.getLogger(__name__)
logging.basicConfig(
        format="%(asctime)s - %(levelname)s: %(message)s",
        filename=log_file, encoding="utf-8", level=logging.INFO)

log_cm = vagrant.make_file_cm(log_file)

@contextlib.contextmanager
def vagrant_run(path):
    abspath = os.path.abspath(path)

    log_cm = vagrant.make_file_cm(abspath+"/vagrant_error.log", 'w')
    v = vagrant.Vagrant(
            root=abspath,  #confirmar que el abspath existe antes, si no existe no hace nada
            # Tampoco manda ninguna clase de error.
            err_cm=log_cm,
            out_cm=vagrant.stdout_cm
            )
    try:
        yield v
    except Exception as err:
        message = ""
        with open(abspath+"/vagrant_error.log") as error:
            for line in error.readlines():
                message = message + line[:-1] + " "
                print(message)
            
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
            "message": message[7:-5],
                }
        )
