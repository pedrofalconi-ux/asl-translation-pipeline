import collections
import csv

from artifact import get_artifact_directory
from elements.element import PipelineElement
from registry import register_element


class FamososAugmentation(PipelineElement):
    '''Data augmentation for famous people.'''
    name = 'famosos_augmentation'

    def __init__(self, *args, **kwargs):
        super().__init__(__file__, *args, **kwargs)

        # counter of names: each item is a tuple of (name, name_without_suffix).
        self._names = collections.Counter()

        # quick explanation: name is used during the search and replace
        # operations in gi (interpreter glosa), while name_without_suffix is
        # used in gr (rule-based glosa), which does not contain suffixes or
        # underscores for special cases (_FAMOSO, _CIDADE etc)

        self._max_new_sentences = int(kwargs['max_new_sentences']) \
            if 'max_new_sentences' in kwargs else None

        try:
            self._path = kwargs['path']
        except KeyError:
            raise ValueError(
                '`famosos_augmentation` requires `path` parameter.'
            )

        # populate self._names with the names in the CSV file specified by _path
        with open(self._path, 'r') as names_file:
            names_reader = csv.reader(names_file)
            for row in names_reader:
                if not row:
                    break

                name = row[0]
                name_without_suffix = row[1]

                self._names[((name, name_without_suffix.replace('_', ' ')))] += 1


    def _search_for_name(self, gr: str, gi: str) -> list:
        '''Search for a name in the given sentence. Returns a tuple for every
        name found.
        '''
        results = []

        for name, name_without_suffix in self._names:
            idx_gi = gi.find(name)
            if idx_gi != -1:
                idx_gr = gr.find(name_without_suffix)

                if idx_gr != -1:
                    results.append((idx_gr, idx_gi, (name, name_without_suffix)))
                else:
                    pass
                    # Happens too often, don't want this noise in the log for now.
                    # logger.warning(f'Found name in gi but not gr (???). gr={gr}')

        return results


    def _generate_sentences(self, gr: str, gi: str, name_tuple: tuple) -> list:
        '''For a given sentence, return a list of new sentences where the name
        specified by `name_tuple` is replaced with the other names in self._names.
        '''
        sentences = set()
        original_name, original_name_without_suffix = name_tuple

        # TODO: shuffle self._names for fairness when truncating beacuse of
        # self._max_new_sentences
        for i, (new_name, new_name_without_suffix) in enumerate(self._names):
            if self._max_new_sentences and i >= self._max_new_sentences:
                break

            sentences.add((
                gr.replace(original_name_without_suffix, new_name_without_suffix),
                gi.replace(original_name, new_name)
            ))

        return sentences


    def process(self, data):
        new_sentences = set()

        for line in data:
            gr, gi = line

            results = self._search_for_name(gr, gi)
            for result in results:
                idx_gr, idx_gi, idx_name = result

                for new_sentence in self._generate_sentences(gr, gi, idx_name):
                    new_sentences.add(new_sentence)

        return list(new_sentences)


# Add element to the registry.
register_element(FamososAugmentation)
