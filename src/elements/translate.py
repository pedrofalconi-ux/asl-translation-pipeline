import logging
import math
import multiprocessing
import os
import traceback

from globalstore import add_to_store, fetch_from_store
from utils import add_submodule_to_sys_path, get_git_revision_hash, get_submodule_path
from elements.element import PipelineElement
from registry import register_element

logger = logging.getLogger(__name__)

def translation_routine(enumerated_data_tuple, tr_instance=None, always_use_tqdm=False):
    '''Entry-point for the translation process, when the element is executed
    with the multiprocessing flag enabled.
    '''
    output = []
    i, data = enumerated_data_tuple

    try:
        # import vlibras-translate and instantiate, if running in a separate process
        if not tr_instance:
            import vlibras_translate
            tr_instance = vlibras_translate.translation.Translation()

        # if running multiprocess, tqdm should only be used in one of them to
        # avoid messing up the stdout
        if always_use_tqdm or i == 0:
            from tqdm import tqdm
            data_iterator = enumerate(tqdm(data, desc='translating'))
        else:
            data_iterator = enumerate(data)

        # actually translate rows
        for i, line in data_iterator:
            if not line or len(line) < 2:
                logger.warn(f'Missing GR/GI, skipping...\nProblematic line: {line}')
                continue

            pt = line[0]
            gi = line[1]
            gr = tr_instance.rule_translation(pt)
            if not gr or not gi:
                logger.warning(f'Missing GR/GI after translating, skipping...\nProblematic line: {line}')
                continue

            output.append((gr, gi))

        return output
    except Exception as ex:
        # for some reason, some specific exceptions don't get caught if we don't
        # do this manually
        logger.error(f'Exception thrown in vlibras-translate subprocess: {ex}')
        traceback.print_exc()

        # re-raise so everything fails correctly
        raise ex

class TranslationElement(PipelineElement):
    '''Translates a list of (PT, GI) tuples to (GR, GI) tuples.'''
    name = 'translate'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Use multiple processes?
        self._multiprocess = 'disable-multiprocessing' not in kwargs

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

    def _single_process_translation(self, data):
        '''Translate the (PT, GI) tuples in `data` using a single process.'''
        return translation_routine(data, tr_instance=self._tr, always_use_tqdm=True)

    def _multi_process_translation(self, data):
        '''Same as above, but using all possible CPU cores.'''
        rows_per_process = math.ceil(len(data) / os.cpu_count())

        # generate slices from the full corpus, so we don't have to copy the
        # entire thing multiple times
        def _enumerated_slice_generator():
            for i in range(os.cpu_count()):
                start_idx = rows_per_process * i
                end_idx = None if i == os.cpu_count() - 1 else rows_per_process * (i + 1)
                yield (i, data[start_idx:end_idx])

        # translate the data slices
        output = []

        # NOTE: yes, I know using fork() is infinitely faster on Unix systems.
        # unfortunately, using fork() causes vlibras-translate to spit out empty
        # translations and I don't have the time to look into that right now.
        with multiprocessing.get_context('spawn').Pool(os.cpu_count()) as pool:
            for translated_slice in pool.imap_unordered(translation_routine, _enumerated_slice_generator()):
                output += translated_slice

        return output

    def process(self, data):
        if self._multiprocess:
            return self._multi_process_translation(data)
        else:
            return self._single_process_translation(data)

# Add element to the registry.
register_element(TranslationElement)
