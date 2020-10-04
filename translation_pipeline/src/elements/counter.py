import logging
import os
import re
import csv

from artifact import get_artifact_directory
from elements.element import PipelineElement
from registry import register_element

logger = logging.getLogger(__name__)

# should be used inside a regex dictionary. note the `-`
REGEX_LATIN = 'A-ZÁÉÍÓÚÀÂÊÔÃÕÜÇa-záéíóúàâêôãõüç'

class CounterElement(PipelineElement):
    '''Takes a list of (GR, GI) tuples, counts special cases and writes out to a
    CSV file.
    '''
    # NOTE: expects directionality in VERB_1S_1S format, itensifiers afterwards
    # and "&" used as context marker.
    name = 'counter'
    dont_use_cache = True

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.homonimous_list = set()

        with open('data/augmentation/homonimos.csv') as f:
            csv_data = csv.reader(f)
            for line in csv_data:
                self.homonimous_list = self.homonimous_list.union({word for word in line})

        if 'filename' not in kwargs:
            raise ValueError(f'`{self.name}` requires a `filename` parameter.')

        self._filename = kwargs['filename']

        self._special_cases = [
            ('Direcionalidade', rf'[{REGEX_LATIN}_]+_[123][SP]_[123][SP]'),
            ('Intensidade', rf'[{REGEX_LATIN}_]+\([-+]\)'),
            ('Negação', rf'NÃO_[{REGEX_LATIN}_]+'),
            ('Famosos', rf'[{REGEX_LATIN}_]+&FAMOS(A|O)'),
            ('Lugares', rf'[{REGEX_LATIN}_]+&(CIDADE|ESTADO|PAÍS)'),
            ('Romanos', rf'^(?=[MDCLXVI])M*(C[MD]|D?C*)(X[CL]|L?X*)(I[XV]|V?I*)$'),
            ('Ordinais', rf'[1-9]+[ºª]'),
            ('Cardinais', rf'[0-9]+$'),
            ('Contexto', rf'(?<!NÃO)(?<![1-3][SP])[_|&](?!\w*PAÍS|\w*ESTADO|\w*CIDADE|\w*[1-3][SP]|\w*[&|_]*FAMOSO)'),
            ('Básico', None)
        ]

    def process(self, data):
        counts = {}

        for pt, gi in data:

            gi_has_matched = False

            # iterate through special cases, check for matches in sentence
            for case_name, case_regex in self._special_cases:
                
                case_found = False
                phrase = pt if case_name == 'Cardinais' or case_name == 'Ordinais' else gi
                
                for word in phrase.split():
                    cleaned_word = re.sub(r'(?<=[0-9])[,.](?![0-9])', '', word)
                    cleaned_word = re.sub(r'[?!":;]', '', cleaned_word)
                    if case_regex and re.search(case_regex, cleaned_word) and case_found == False:
                        gi_has_matched = True
                        point = 1
                        case_found = True
                        if case_name == 'Contexto':
                            point = 1 if word in self.homonimous_list else 0                            
                        try:
                            counts[case_name] += point
                        except KeyError:
                            counts[case_name] = point

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
