import contextlib
import vagrant
import os
import logging
from jinja2 import Environment, FileSystemLoader
from pydantic import BaseModel

log = logging.getLogger(__name__)
logging.basicConfig(filename="/vagrant/logs/api.log", encoding="utf-8", level=logging.DEBUG)

log_cm = vagrant.make_file_cm("/vagrant/logs/api.log")

def check_dir(path) -> bool:
    if os.path.isdir(path):
        return True
    else: return False



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
    cpu: int | None = None
    mem: int | None = None
    boxname: str | None = None
    hostname: str | None = None

# Convertir en cm para cambiar de directorio?
def load_template(temp_info):
    env = Environment(loader=FileSystemLoader("/vagrant/src/templates/"))
    template = env.get_template("vagrantfile.template")
    
    if temp_info == None:
        temp_info = Temp_info()
    contenido = template.render(temp_info)

    file = open("Vagrantfile", "w")
    file.write(contenido)
