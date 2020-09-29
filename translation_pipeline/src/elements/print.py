import csv

from elements.element import PipelineElement
from registry import register_element
from utils import get_file_md5_hash

class PrintElement(PipelineElement):
    '''Debug element, prints out some text.'''
    name = 'print'
    dont_use_cache = True

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        try:
            self._text = kwargs['text']
        except KeyError:
            raise ValueError(f'`{self.name}` requires a `text` parameter.')

    def process(self, data=[]):
        print(self._text)

        return data

# Add element to the registry.
register_element(PrintElement)
