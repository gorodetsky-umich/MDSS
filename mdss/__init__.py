__version__ = "0.1.0"

from .src import main
from .utils import utils
from .src.main import simulation
from .src.main import post_process
from .src.main_helper import execute
try:
    from .src.aerostruct import Problem # Requires mphys and other libraries. Causes problems when using in a different environment.
except:
    pass

__all__ = ["main", "utils", "Problem", "simulation", "execute", "post_process"]