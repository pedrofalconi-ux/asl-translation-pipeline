import os

from artifact import get_artifact_directory
from elements.element import PipelineElement
from registry import register_element

class ParallelFileDestElement(PipelineElement):
    '''Writes out GR and GI files.'''
    name = 'parallel_filedest'

    _gr_fd = None
    _gi_fd = None
    _gr_path = None
    _gi_path = None
    _complete_gr_path = None
    _complete_gi_path = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        try:
            self._gr_path = kwargs['gr_path']
            self._gi_path = kwargs['gi_path']

            self._complete_gr_path = os.path.join(get_artifact_directory(), self._gr_path)
            os.makedirs(os.path.dirname(self._complete_gr_path), exist_ok=True)
            self._complete_gi_path = os.path.join(get_artifact_directory(), self._gi_path)
            os.makedirs(os.path.dirname(self._complete_gi_path), exist_ok=True)

        except KeyError:
            raise ValueError('`csvdest` requires a `gr_path` and `gi_path` parameter.')


    def process(self, data):
        with open(self._complete_gr_path, 'w') as self._gr_fd, open(self._complete_gi_path, 'w') as self._gi_fd:
            for line in data:
                self._gr_fd.write(f'{line[0]}\n')
                self._gi_fd.write(f'{line[1]}\n')


# Add element to the registry.
register_element(ParallelFileDestElement)
