import csv

from elements.element import PipelineElement
from registry import register_element
from utils import get_file_md5_hash

class CsvSrcElement(PipelineElement):
    '''Reads from a `.csv` file.'''
    name = 'csvsrc'
    dont_cache_output = True

    _fd = None
    _reader = None
    _path = None

    def __init__(self, *args, **kwargs):
        super().__init__(args, *kwargs)

        try:
            self._path = kwargs['path']
            self._fd = open(self._path, 'r')
            self._reader = csv.reader(self._fd)
        except KeyError:
            raise ValueError('`csvsrc` requires a `path` parameter.')

    def get_cache_key(self):
        # Cache key is the MD5 hash of the file itself. This way, even if the
        # path changes we can still get a cache hit if the file itself is the
        # same.
        return get_file_md5_hash(self._path)

    def process(self, data=None):
        return self._reader

    def __del__(self):
        if self._fd:
            self._fd.close()

# Add element to the registry.
register_element(CsvSrcElement)
