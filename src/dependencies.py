import contextlib
from fastapi import HTTPException
import vagrant
import os
import shutil
import logging
from dotenv import load_dotenv

load_dotenv()

log_file = os.getenv("LOG_FILE")
if log_file is None:
    raise RuntimeError("La variable de entorno LOG_FILE no se ha cargado.")


log = logging.getLogger(__name__)
logging.basicConfig(filename=log_file, encoding="utf-8", level=logging.DEBUG)

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
        v.destroy()
        shutil.rmtree(path)
        log.exception(err.args)
        raise HTTPException(status_code=400, detail={
            "message": f"El comando 'vagrant {err.args[1][1]} {err.args[1][2]}' ha devuelto estado de salida {err.args[0]}.",
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


