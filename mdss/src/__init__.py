# src/__init__.py
from .main import simulation, post_process
try:
    from .aerostruct import Problem
except:
    pass

__all__ = ["simulation", "post_process", "Problem"]