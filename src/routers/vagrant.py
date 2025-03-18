import vagrant
import os
from fastapi import APIRouter
from ..dependencies import change_of_dir


router = APIRouter()

@router.get("/vagrant/create")
def create_vm(dir: str | None = None):
    with change_of_dir():
        os.chdir(dir)
        v = vagrant.Vagrant(quiet_stdout=False, quiet_stderr=False)
        v.up()
    return {"Hello": "World"}
    
