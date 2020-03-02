'''Miscellaneous utility functions.'''
import os
import subprocess
import sys

def get_git_revision_hash(cwd=None, short=False):
    '''Returns the current git revision hash of this repository. If desired, the
    hash for other repositories can be obtained by using the `cwd` argument.'''
    popenargs = ['git', 'rev-parse', 'HEAD']
    if short:
        popenargs.append('--short')

    return subprocess.check_output(popenargs, cwd=cwd).decode('utf-8').strip()

def add_submodule_to_sys_path(submodule_name):
    '''Adds the given `submodule_name` to the sys's import PATH.'''
    sys.path.insert(0, os.path.realpath(
        os.path.join(os.path.dirname(__file__), '..', 'submodules', submodule_name))
    )
