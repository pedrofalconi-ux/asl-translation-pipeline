import csv
import os

from artifact import get_artifact_directory
from elements.element import PipelineElement
from registry import register_element
from utils import add_submodule_to_sys_path

class ResultsElement(PipelineElement):
    '''Output CSV file with test results.'''
    name = 'results'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        try:
            # Original test corpus, for extracting the PT-BR column
            self._corpus_path = os.path.join(get_artifact_directory(), kwargs['corpus_file'])

            self._gr_path = os.path.join(get_artifact_directory(), 'Preprocessed/test.gr')
            self._gi_model_path = os.path.join(get_artifact_directory(), 'test.h')

            self._results_csv_path = os.path.join(get_artifact_directory(), 'Test Results.csv')
        except KeyError:
            raise ValueError('`results` requires a `corpus_file` parameter.')

        from strsimpy.levenshtein import Levenshtein
        self._levenshtein = Levenshtein()

        add_submodule_to_sys_path('vlibras-translate')
        from vlibras_translate import postprocessing
        self._postprocessor = postprocessing.Postprocessor()


    def _calculate_scores(self, gi_model, gi_gold):
        return (100 - self._levenshtein.distance(gi_model, gi_gold)) / 100


    def process(self, data=None):
        with open(self._corpus_path, 'r') as test_corpus_file, \
            open(self._gr_path, 'r') as gr_file, \
            open(self._gi_model_path, 'r') as gi_model_file, \
            open(self._results_csv_path, 'w') as results_csv_file:
            test_corpus_reader = csv.reader(test_corpus_file)
            csv_writer = csv.writer(results_csv_file)
            csv_writer.writerow(
                ['PT', 'GR', 'GI (Padrão Ouro)', 'GI (Gerado pela rede)', 'Score', 'Resultado']
            )

            result_count = {
                'OK': 0,
                'Parcial': 0,
                'Incorreto': 0,
            }
            total_results = 0

            for row in test_corpus_reader:
                pt = row[0]
                gi_gold = row[1]
                gr = gr_file.readline().strip()
                gi_model = self._postprocessor.postprocess(gi_model_file.readline().strip())

                score = self._calculate_scores(gi_model, gi_gold)
                if score == 1:
                    result = 'OK'
                elif score > 0.85:
                    result = 'Parcial'
                else:
                    result = 'Incorreto'
                result_count[result] += 1
                total_results += 1

                csv_writer.writerow([
                    pt, gr, gi_gold, gi_model,
                    f'{round(score * 100, 2)}%',
                    result
                ])

            csv_writer.writerow([''])
            for result in result_count:
                csv_writer.writerow([f'{result}: {round(100 * result_count[result] / total_results, 2)}%'])

# Add element to the registry.
register_element(ResultsElement)
