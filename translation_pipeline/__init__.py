import os
import sys

# add "src" to the import path to avoid messing with the imports for now. should fix later
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'src'))

# expose top-level "execute" function
from .src.cli import execute

# expose other internal stuff
from .src import *
