"""
小說寫作器主模組
"""

from .models import *
from .services import *
from .core import *
from .utils import *

# UI模組在需要時再導入，因為需要tkinter
# from .ui import *

__version__ = "3.0.0"