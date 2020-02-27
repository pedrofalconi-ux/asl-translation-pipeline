'''Miscellaneous utility functions.'''
import subprocess

def get_git_revision_hash(cwd=None, short=False):
    '''Returns the current git revision hash of this repository. If desired, the
    hash for other repositories can be obtained by using the `cwd` argument.'''
    popenargs = ['git', 'rev-parse', 'HEAD']
    if short:
        popenargs.append('--short')

    return subprocess.check_output(popenargs, cwd=cwd, text=True).strip()
