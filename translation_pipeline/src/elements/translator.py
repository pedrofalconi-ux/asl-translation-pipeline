import logging
import math
import multiprocessing
import os
import traceback

from elements.element import PipelineElement
from globalstore import add_to_store, fetch_from_store
from registry import register_element
from utils import add_submodule_to_sys_path, get_git_revision_hash, get_submodule_path

logger = logging.getLogger(__name__)


def translation_routine(enumerated_data_tuple, tr_instance=None, always_use_tqdm=False):
    """Entry-point for the translation process, when the element is executed
    with the multiprocessing flag enabled.
    """
    output = []
    i, data = enumerated_data_tuple

    try:
        # import vlibras-translate and instantiate, if running in a separate process
        if not tr_instance:
            import vlibras_translator

            tr_instance = vlibras_translator.translate.Translator()

        # if running multiprocess, tqdm should only be used in one of them to
        # avoid messing up the stdout
        if always_use_tqdm or i == 0:
            from tqdm import tqdm

            data_iterator = enumerate(tqdm(data, desc="translating"))
        else:
            data_iterator = enumerate(data)

        # actually translate rows
        for j, line in data_iterator:
            # execute progress callback, if it exists (but only in one of the threads)
            if always_use_tqdm or i == 0:
                progress_callback_fn = fetch_from_store("progress_callback_fn")
                if progress_callback_fn:
                    progress_callback_fn(
                        {"name": "translate", "progress": j / len(data)}
                    )

            if not line or len(line) < 2:
                logger.warn(f"Missing GR/GI, skipping...\nProblematic line: {line}")
                continue

            pt = line[0]
            gi = line[1]
            gr = tr_instance.translate(pt, neural=False)
            if not gr or not gi:
                logger.warning(
                    f"Missing GR/GI after translating, skipping...\nProblematic line: {line}"
                )
                continue

            output.append((gr, gi))

        return output
    except Exception as ex:
        # for some reason, some specific exceptions don't get caught if we don't
        # do this manually
        logger.error(f"Exception thrown in vlibras-translate subprocess: {ex}")
        traceback.print_exc()

        # re-raise so everything fails correctly
        raise ex


class TranslatorElement(PipelineElement):
    """Translates a list of (PT, GI) tuples to (GR, GI) tuples."""

    name = "translator"
    version = 1

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Use multiple processes?
        self._multiprocess = "disable-multiprocessing" not in kwargs

        # Check for vlibras-translate.
        self._tr = fetch_from_store("vlibras-translator-instance")
        if not self._tr:
            from vlibras_translator import translate
            self._tr = translate.Translator()
            add_to_store("vlibras-translator-instance", self._tr)

    def _single_process_translation(self, data):
        """Translate the (PT, GI) tuples in `data` using a single process."""
        return translation_routine(data, tr_instance=self._tr, always_use_tqdm=True)

    def _multi_process_translation(self, data):
        """Same as above, but using all possible CPU cores."""
        rows_per_process = math.ceil(len(data) / os.cpu_count())

        # generate slices from the full corpus, so we don't have to copy the
        # entire thing multiple times
        def _enumerated_slice_generator():
            for i in range(os.cpu_count()):
                start_idx = rows_per_process * i
                end_idx = (
                    None if i == os.cpu_count() - 1 else rows_per_process * (i + 1)
                )
                yield (i, data[start_idx:end_idx])

        # translate the data slices
        output = []

        # NOTE: yes, I know using fork() is infinitely faster on Unix systems.
        # unfortunately, using fork() causes vlibras-translate to spit out empty
        # translations and I don't have the time to look into that right now.
        with multiprocessing.get_context("spawn").Pool(os.cpu_count()) as pool:
            for translated_slice in pool.imap(
                translation_routine, _enumerated_slice_generator()
            ):
                output += translated_slice

        return output

    def process(self, data):
        if self._multiprocess:
            return self._multi_process_translation(data)
        else:
            return self._single_process_translation(data)


# Add element to the registry.
register_element(TranslatorElement)
