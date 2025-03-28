from typing import Annotated
from fastapi import APIRouter, Depends
from sqlmodel import Field, SQLModel, create_engine, Session

router = APIRouter()

class Vm(SQLModel, table=True):
    vm_id: int = Field(primary_key=True)
    vm_name: str = Field(index=True)
    cpu: int
    mem: int
    space: int
    env_id: int = Field(foreign_key="venv.env_id")

class Venv(SQLModel, table=True):
    env_id: int = Field(primary_key=True)
    env_name: str = Field(index=True)
    host_id: int = Field(foreign_key="host.host_id")

class Host(SQLModel, table=True):
    host_id: int = Field(primary_key=True)
    cpu_total: int
    mem_total: int
    space_total: int
    free_cpu: int
    free_mem: int
    free_space: int

sqlite_file_name = "db.db"
sqlite_url = f"sqlite:///{sqlite_file_name}"

engine = create_engine(sqlite_url, echo=True)

# Esto crea una sesión y la devuelve, para que al acabar la petición se libere automáticamente
def get_session():
    with Session(engine) as session:
        yield session

# Esto evita tener que crear el annotated y llamar al Depends en cada petición
# Llama a get_session y devuelve su sesión, para usarla en cada petición de forma individual
SessionDep = Annotated[Session, Depends(get_session)]
