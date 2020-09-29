'''Miscellaneous utility functions.'''
import os
import subprocess
import sys

modules_in_path = set()

def get_file_md5_hash(file, cwd=None):
    '''Returns the MD5 hash for the specified file.'''
    return subprocess.check_output(['rhash', '--md5', file], cwd=cwd).decode('utf-8').strip()

def get_git_revision_hash(cwd=None, short=False):
    '''Returns the current git revision hash of this repository. If desired, the
    hash for other repositories can be obtained by using the `cwd` argument.'''
    popenargs = ['git', 'rev-parse', 'HEAD']
    if short:
        popenargs.append('--short')

    return subprocess.check_output(popenargs, cwd=cwd).decode('utf-8').strip()

def get_submodule_path(submodule_name):
    '''Gets the path to the submodule named `submodule_name`.'''
    return os.path.realpath(
        os.path.join(os.path.dirname(__file__), '..', 'submodules', submodule_name)
    )

def add_submodule_to_sys_path(submodule_name):
    '''Adds the given `submodule_name` to the sys's import PATH.'''
    if submodule_name in modules_in_path:
        return

    sys.path.insert(0, get_submodule_path(submodule_name))
    modules_in_path.add(submodule_name)

def resolve_relative_path(relative_path):
    '''Resolves a relative path, using the pipeline module folder as the root
    directory.
    '''
    if relative_path.startswith('/') or relative_path.startswith('\\'):
        # already an absolute path, bail
        return relative_path

    return os.path.realpath(
        os.path.join(os.path.dirname(__file__), '..', relative_path)
    )
