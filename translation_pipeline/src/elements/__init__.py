import glob
from os.path import basename, dirname, isfile, join

# Put all element modules into the __all__ variable (used when importing *)
modules = glob.glob(join(dirname(__file__), "*.py"))
__all__ = [
    basename(f)[:-3]
    for f in modules
    if isfile(f) and (not f.endswith("__init__.py") and not f.endswith("element.py"))
]
