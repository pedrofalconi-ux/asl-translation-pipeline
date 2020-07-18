import logging

from globalstore import add_to_store, fetch_from_store
from utils import add_submodule_to_sys_path, get_git_revision_hash, get_submodule_path
from elements.element import PipelineElement
from registry import register_element

logger = logging.getLogger(__name__)

class TranslationElement(PipelineElement):
    '''Translates a (PT, GI) tuple to a (GR, GI) tuple.'''
    name = 'translate'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Import TQDM.
        from tqdm import tqdm
        self._tqdm = tqdm

        # Check for vlibras-translate.
        self._tr = fetch_from_store('vlibras-translation-instance')
        if not self._tr:
            # Module wasn't loaded. Import it and save to the global store.
            add_submodule_to_sys_path('vlibras-translate')

            from vlibras_translate import translation
            self._tr = translation.Translation()

            add_to_store('vlibras-translation-instance', self._tr)

    def get_cache_key(self):
        # Given the same input data, the output should only change if when the
        # version of the `vlibras-translate` submodule changes. We account for
        # this by using the git HEAD commit hash as the cache key.
        return get_git_revision_hash(cwd=get_submodule_path('vlibras-translate'))

    def process(self, data):
        output = []

        for i, line in enumerate(self._tqdm(data, desc='translating')):
            if not line or len(line) < 2:
                logger.warn(f'Missing GR/GI in line {i + 1}, skipping...\nProblematic line: {line}')
                continue


            pt = line[0]
            gi = line[1]
            gr = self._tr.rule_translation(pt)

            if not gr or not gi:
                logger.warning(f'Missing GR/GI in line {i + 1} after translating, skipping...')
                continue

            output.append((gr, gi))

        return output

# Add element to the registry.
register_element(TranslationElement)
