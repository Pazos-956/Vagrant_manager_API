import os
from fastapi import APIRouter, HTTPException, status
from fastapi.responses import JSONResponse

router = APIRouter()

base_path = os.getenv("USERS_PATH")

@router.post("/users/create-user/{usr}")
def create_user_dir(usr: str):
    assert base_path
    usr_path = os.path.normpath(base_path+usr)
    if os.path.exists(usr_path):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail={
            "message": "No se ha encontrado el usuario.",
            "user": usr
        })
    os.mkdir(usr_path)
    
    return JSONResponse(status_code=status.HTTP_201_CREATED,
                        content={
                            "message": "El usuario se ha creado correctamente.",
                            "user": usr,
                        })

@router.delete("/users/{usr}/delete",status_code=status.HTTP_204_NO_CONTENT)
def remove_user_dir(usr: str):
    assert base_path
    usr_path = os.path.normpath(base_path+usr)
    if not os.path.exists(usr_path):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={
            "message": "No se ha encontrado el usuario.",
            "user": usr
        })
    try:
        os.rmdir(usr_path)
    except OSError as err:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail={
            "message": "No se ha podido borrar el usuario, comprueba que se han eliminado todos sus entornos.",
            "user": usr
        })
    return
    
