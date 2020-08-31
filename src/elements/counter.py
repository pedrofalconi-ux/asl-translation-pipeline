import logging
import os
import re

from artifact import get_artifact_directory
from elements.element import PipelineElement
from registry import register_element

logger = logging.getLogger(__name__)

# should be used inside a regex dictionary. note the `-`.`
REGEX_LATIN = 'A-ZÁÉÍÓÚÀÂÊÔÃÕÜÇa-záéíóúàâêôãõüç'

class CounterElement(PipelineElement):
    '''Takes a list of (GR, GI) tuples, counts special cases and writes out to a
    CSV file.
    '''
    # NOTE: expects directionality in VERB_1S_1S format, itensifiers afterwards
    # and "&" used as context marker.
    name = 'counter'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if 'filename' not in kwargs:
            raise ValueError(f'`{self.name}` requires a `filename` parameter.')

        self._filename = kwargs['filename']

        self._special_cases = [
            ('Direcionalidade', rf'[{REGEX_LATIN}_]+_[123][SP]_[123][SP]'),
            ('Intensidade', rf'[{REGEX_LATIN}_]+\([-+]\)'),
            ('Negação', rf'NÃO_[{REGEX_LATIN}_]+'),
            ('Famosos', rf'[{REGEX_LATIN}_]+&FAMOS(A|O)'),
            ('Lugares', rf'[{REGEX_LATIN}_]+&(CIDADE|ESTADO|PAÍS)'),
            ('Básico', None)
        ]

    def process(self, data):
        counts = {}

        for _, gi in data:
            gi_has_matched = False

            # iterate through special cases, check for matches in sentence
            for case_name, case_regex in self._special_cases:
                if case_regex and re.match(case_regex, gi):
                    gi_has_matched = True
                    try:
                        counts[case_name] += 1
                    except KeyError:
                        counts[case_name] = 1

            # didn't match any of the special cases, count as regular sentence
            if not gi_has_matched:
                try:
                    counts['Básico'] += 1
                except KeyError:
                    counts['Básico'] = 1

        # write to file
        filepath = os.path.join(get_artifact_directory(), self._filename)
        os.makedirs(os.path.dirname(filepath), exist_ok=True)

        with open(filepath, 'w') as fd:
            fd.write('Caso,Ocorrências\n')
            for case_name, case_count in counts.items():
                fd.write(f'{case_name},{case_count}\n')

        # forward output
        return data

# Add element to the registry.
register_element(CounterElement)
