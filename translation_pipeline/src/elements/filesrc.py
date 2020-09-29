from elements.element import PipelineElement
from registry import register_element
from utils import get_file_md5_hash, resolve_relative_path

class FileSrcElement(PipelineElement):
    '''Reads from a file.'''
    name = 'filesrc'
    dont_use_cache = True

    _path = None
    _binary = False
    _fd = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        try:
            self._path = resolve_relative_path(kwargs['path'])
            self._binary = getattr(kwargs, 'binary', False)
            self._fd = open(kwargs['path'], 'rb' if self._binary else 'r')
        except KeyError:
            raise ValueError('`filesrc` requires a `path` parameter.')

    def get_cache_key(self):
        # Cache key is the MD5 hash of the file itself. This way, even if the
        # path changes we can still get a cache hit if the file itself is the
        # same.
        key = get_file_md5_hash(self._path)
        if self._binary:
            # However, we also need to take into account the `binary` parameter.
            # Changing it will cause the output of this element to change, and
            # as such, the cache key should also change.
            key += 'b'

        return key

    def process(self, data=None):
        if self._binary:
            return self._fd.read()
        return self._fd.readlines()

    def __del__(self):
        if self._fd:
            self._fd.close()

# Add element to the registry.
register_element(FileSrcElement)
