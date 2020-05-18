import csv
import os

from artifact import get_artifact_directory
from elements.element import PipelineElement
from registry import register_element

class ResultsElement(PipelineElement):
    '''Output CSV file with test results.'''
    name = 'results'

    _corpus_path = None
    _pt_path = None
    _gr_path = None
    _gi_path = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        try:
            self._corpus_path = os.path.join(get_artifact_directory(), kwargs['corpus_file'])
            self._pt_path = os.path.join(get_artifact_directory(),) #TODO: pegar o arquivo onde fica as frases pt-br
            self._gr_path = os.path.join(get_artifact_directory(), 'Preprocessed/test.gr')
            self._gi_path = os.path.join() #TODO: pegar o arquivo gi resultante do treino

        except KeyError:
            raise ValueError('`results` requires a `corpus_file` parameter.')

    def process(self, data):
        with open(self._corpus_path, 'r') as test_corpus, \
            open(self._pt_path, 'r') as pt_file, \
            open(self._gr_path, 'r') as gr_file, \
            open(self._gi_path, 'r') as gi_file:
            # ...
            print()


# Add element to the registry.
register_element(ResultsElement)
