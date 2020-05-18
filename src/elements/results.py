import csv
import os

from artifact import get_artifact_directory
from elements.element import PipelineElement
from registry import register_element

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


    def _calculate_scores(self, gi_model, gi_gold):
        set_gold = set()
        set_model = set()

        correct = 0
        total = 0

        words_model = gi_model.split()
        for i, word_gold in enumerate(gi_gold.split()):
            total += 1
            set_gold.add(word_gold)

            try:
                word_model = words_model[i]
            except IndexError:
                continue

            set_model.add(word_model)
            if word_model == word_gold:
                correct += 1

        position_dependent_score = correct / total
        position_independent_score = 1 - (len(set_gold - set_model) / len(set_gold))

        return position_dependent_score, position_independent_score


    def process(self, data=None):
        with open(self._corpus_path, 'r') as test_corpus_file, \
            open(self._gr_path, 'r') as gr_file, \
            open(self._gi_model_path, 'r') as gi_model_file, \
            open(self._results_csv_path, 'w') as results_csv_file:
            test_corpus_reader = csv.reader(test_corpus_file)
            csv_writer = csv.writer(results_csv_file)
            csv_writer.writerow(
                ['PT', 'GR', 'GI (Padrão Ouro)', 'GI (Gerado pela rede)', 'Score (por pos.)', 'Score (por dic.)', 'Resultado']
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
                gi_model = gi_model_file.readline().strip()

                score_pos_dependent, score_pos_independent = self._calculate_scores(gi_model, gi_gold)
                if score_pos_dependent == 1:
                    result = 'OK'
                elif score_pos_independent > 0.5:
                    result = 'Parcial'
                else:
                    result = 'Incorreto'
                result_count[result] += 1
                total_results += 1

                csv_writer.writerow([
                    pt, gr, gi_gold, gi_model,
                    f'{round(score_pos_dependent * 100, 2)}%',
                    f'{round(score_pos_independent * 100, 2)}%',
                    result
                ])

            csv_writer.writerow([''])
            for result in result_count:
                csv_writer.writerow([f'{result}: {round(100 * result_count[result] / total_results, 2)}%'])

# Add element to the registry.
register_element(ResultsElement)
