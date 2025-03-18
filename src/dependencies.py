import contextlib
import os

@contextlib.contextmanager
def change_of_dir():
    old_dir = os.getcwd()
    try:
        yield
    except:
        print("Error al cambiar de directorio")
    finally:
        os.chdir(old_dir)
