import csv
import logging
import re

from elements.element import PipelineElement
from globalstore import add_to_store, fetch_from_store
from registry import register_element
from utils import add_submodule_to_sys_path, resolve_relative_path

logger = logging.getLogger(__name__)


class PreprocessElement(PipelineElement):
    """Takes a list of (GR, GI) tuples and applies a few modifications before
    training. See methods below to know what they are.
    """

    name = "preprocess"

    def _prepare_homonyms_dict(self, homonyms_csv_filepath):
        """Prepares context pairs in a dictionary, for context marker
        replacement.
        """
        homonyms_dict = {}

        with open(homonyms_csv_filepath, "r") as homonimos_file:
            reader = csv.reader(homonimos_file)
            for row in reader:
                base_word = None
                for col in row:
                    # skip empty columns
                    if not col:
                        continue

                    # save first column as base word
                    if not base_word:
                        base_word = col
                        continue

                    suffix = col[len(base_word) :]
                    if "&" in col:
                        homonym_with_context_marker = col
                    else:
                        homonym_with_context_marker = (
                            f"{base_word}{re.sub(r'_', r'&', suffix, count=1)}"
                        )

                    homonyms_dict[
                        f"{base_word}{suffix}".replace("&", "_").upper()
                    ] = homonym_with_context_marker.upper()

        return homonyms_dict

    def _replace_context_markers(self, sentence):
        """Replaces context markers: PODER_INFLUÊNCIA -> PODER&INFLUÊNCIA"""
        replaced_sentence = []

        # replace known context pairs
        for word in sentence.split():
            try:
                replaced_sentence.append(self._homonyms[word])
            except KeyError:
                replaced_sentence.append(word)

        replaced_sentence = " ".join(replaced_sentence)

        # replace for places and people
        replaced_sentence = re.sub(
            r"(\w+)_(CIDADE|ESTADO|PAÍS|FAMOSO)", r"\1&\2", replaced_sentence
        )
        return replaced_sentence

    def _move_intensifiers_to_the_right(self, sentence):
        """Move intensifiers: (++)GRANDE -> GRANDE(++)"""
        return re.sub(r"(\([+-]+\))(\w+)", r"\2\1", sentence)

    def _replace_directionality_syntax(self, sentence):
        """Change directionality syntax: 1S_DO_QUE_3P -> DO_QUE_1S_3P"""
        sentence = re.sub(
            r"([123][SP])_([\w)(&+-]+)_([123][SP])", r"\2_\1_\3", sentence
        )

        return sentence

    def _spell_out_numbers(self, sentence):
        split_sentence = [[x, ""] for x in sentence.split()]
        split_sentence = self._number.to_extenso(split_sentence)

        return " ".join([x[0] for x in split_sentence])

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Figure out which preprocessing steps we should apply.
        self._methods = []

        if "replace_context_markers" in kwargs:
            self._methods.append(self._replace_context_markers)

            # Instantiate context pairs for context marker replacement.
            try:
                self._homonyms = self._prepare_homonyms_dict(
                    resolve_relative_path(kwargs["homonyms_csv_path"])
                )
            except AttributeError:
                raise ValueError(
                    "`preprocess` requires a `homonyms_csv_path` parameter if `replace_context_markers` is enabled."
                )

        if "spell_out_numbers" in kwargs:
            self._methods.append(self._spell_out_numbers)

            # Prepare an instance of Number for spelling out numbers.
            add_submodule_to_sys_path("vlibras-translate")
            import vlibras_translate

            self._number = vlibras_translate.number.Number(cardinal=False)

        if "move_intensifiers_to_the_right" in kwargs:
            self._methods.append(self._move_intensifiers_to_the_right)

        if "replace_directionality_syntax" in kwargs:
            self._methods.append(self._replace_directionality_syntax)

    def process(self, data):
        output = []

        for line in data:
            gr, gi = line

            for method in self._methods:
                gr, gi = (gr, method(gi))
            output.append((gr, gi))

        return output


# Add element to the registry.
register_element(PreprocessElement)
