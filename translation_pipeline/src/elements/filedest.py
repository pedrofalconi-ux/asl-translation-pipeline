import os

from artifact import get_artifact_directory
from elements.element import PipelineElement
from registry import register_element

class FileDestElement(PipelineElement):
    '''Writes out to a file.'''
    name = 'filedest'
    dont_use_cache = True

    _fd = None
    _binary = False
    _path = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        try:
            self._path = kwargs['path']
            self._binary = getattr(kwargs, 'binary', False)
            complete_path = os.path.join(get_artifact_directory(), self._path)
            os.makedirs(os.path.dirname(complete_path), exist_ok=True)

            self._fd = open(complete_path, 'wb' if self._binary else 'w')
        except KeyError:
            raise ValueError('`filedest` requires a `path` parameter.')

    def process(self, data):
        if self._binary:
            self._fd.write(data)
        else:
            for line in data:
                self._fd.write(line)

    def __del__(self):
        if self._fd:
            self._fd.close()

# Add element to the registry.
register_element(FileDestElement)
