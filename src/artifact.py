import hashlib
import os
import shutil

# FIXME: For some reason, having this as a local variable causes an
# UnboundLocalError exception when using it, but ONLY in the `update_hash`
# function (???).
global current_hash
current_hash = ''

def update_hash(appended_hash):
    '''Update the current hash value to take in account the new `appended_hash`.'''
    global current_hash
    current_hash = hashlib.sha1((current_hash + appended_hash).encode('utf-8')).hexdigest()

def get_artifact_directory():
    '''Get path of the temporary artifact directory.'''
    return os.path.join(os.path.dirname(__name__), 'artifacts', 'tmp')

def empty_temporary_artifact_directory():
    '''Deletes the `tmp` artifact directory.'''
    shutil.rmtree(os.path.join(os.path.dirname(__name__), 'artifacts', 'tmp'), ignore_errors=True)
    os.makedirs(os.path.join(os.path.dirname(__name__), 'artifacts', 'tmp'), exist_ok=True)

def rename_temporary_artifact_directory():
    '''Rename the temporary artifact directory to the current hash.'''
    original_dirname = os.path.join(os.path.dirname(__name__), 'artifacts', 'tmp')
    new_dirname = os.path.join(os.path.dirname(__name__), 'artifacts', current_hash)

    os.rename(original_dirname, new_dirname)
