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

def get_artifact_directory_by_hash(artifact_hash):
    '''Returns the path of the artifact directory from a previous execution.'''
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'artifacts', artifact_hash)

def get_artifact_directory():
    '''Returns the path of the current (temporary) artifact directory.'''
    return get_artifact_directory_by_hash('tmp')

def empty_temporary_artifact_directory():
    '''Deletes the `tmp` artifact directory.'''
    shutil.rmtree(get_artifact_directory(), ignore_errors=True)
    os.makedirs(get_artifact_directory(), exist_ok=True)

def rename_temporary_artifact_directory():
    '''Rename the temporary artifact directory to the current hash. Returns the
    `current_hash`, used to rename the directory.
    '''
    original_dirname = get_artifact_directory()
    new_dirname = get_artifact_directory_by_hash(current_hash)

    try:
        os.rename(original_dirname, new_dirname)
    except OSError as ex:
        # TODO: think carefully about how we want to handle this case
        # FIXME: make this not platform-dependent
        if ex.errno == 66:
            pass # Ignore "Directory not empty" errors.
        else:
            raise ex

    return current_hash
