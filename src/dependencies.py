import contextlib
import vagrant
import os
import logging
from jinja2 import Environment, FileSystemLoader
from pydantic import BaseModel

log = logging.getLogger(__name__)
logging.basicConfig(filename="/vagrant/logs/api.log", encoding="utf-8", level=logging.DEBUG)

log_cm = vagrant.make_file_cm("/vagrant/logs/api.log")

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
        log.exception(err.args)
        raise


class Temp_info(BaseModel):
    cpu: int = 1
    mem: int = 1024
    boxname: str = "generic/rocky8"
    hostname: str 
    provider: str = "virtualbox"

def load_template(path, temp_info):
    env = Environment(loader=FileSystemLoader("/vagrant/src/templates/"))
    template = env.get_template("vagrantfile.template")
    contenido = template.render(temp_info)

    vfile = os.path.abspath(path+"/Vagrantfile")
    with open(vfile, "w") as file:
        file.write(contenido)
