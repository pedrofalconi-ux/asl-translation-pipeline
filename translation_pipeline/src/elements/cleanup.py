import logging
import re

from elements.element import PipelineElement
from globalstore import add_to_store, fetch_from_store
from registry import register_element
from utils import add_submodule_to_sys_path

logger = logging.getLogger(__name__)


class CleanupElement(PipelineElement):
    """Takes a list of (GR, GI) tuples and fixes common errors in the sentences."""

    name = "cleanup"
    version = 2

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def _fix_commas(self, sentence):
        sentence = re.sub(r" {2,}", " ", sentence)
        sentence = re.sub(r"( VÍRGULA){2,}", " VÍRGULA", sentence)
        sentence = re.sub(r"(?<=\w),(?=\w)", " VÍRGULA ", sentence)
        sentence = re.sub(r",(?=\w)", "VÍRGULA ", sentence)
        sentence = re.sub(r"(?<=\w),", " VÍRGULA", sentence)

        return sentence

    def _fix_incorrect_directionals(self, sentence):
        return re.sub(r"([SP])([123])", r"\2\1", sentence)

    def _fix_linebreaks(self, sentence):
        return sentence.replace("\r", "").replace("\n", " ")

    def _fix_misplaced_spaces(self, sentence):
        sentence = re.sub(r" _CIDADE", "_CIDADE", sentence)
        sentence = re.sub(r" _ESTADO", "_ESTADO", sentence)
        sentence = re.sub(r" _PAÍS", "_PAÍS", sentence)

        sentence = re.sub(r" _(?=[123][sp])", "_", sentence)

        # TODO: this fixes cases like '(+) GRANDE' -> '(+)GRANDE'. However,
        # currently input data contains sentences with intensifiers both on the
        # right and on the left, so we're skipping this fixup for now.
        # sentence = re.sub(r'(\([+-]+\)) ', r'\1', sentence)

        return sentence

    def _fix_punctuation(self, sentence):
        for punctuation in ["[PONTO]", "[INTERROGAÇÃO]", "[EXCLAMAÇÃO]"]:
            sentence = re.sub(r"(?<=\w),(?=\w)", f" {punctuation} ", sentence)
            sentence = re.sub(r",(?=\w)", f"{punctuation} ", sentence)
            sentence = re.sub(r"(?<=\w),", f" {punctuation}", sentence)

        for match in re.finditer(r"(?<=\[)\w+(?=\])", sentence):
            match_found = match.group()

            if match_found not in ["PONTO", "INTERROGAÇÃO", "EXCLAMAÇÃO"]:
                logger.warning(
                    "Incorrect punctuation found: `%s` in sentence `%s`",
                    match_found,
                    sentence,
                )
                return None

        return sentence

    def _remove_futuro_passado(self, gr, gi):
        def _check_line(rule, interp):
            rule_fp = ("FUTURO" in rule) or ("PASSADO" in rule)
            interp_fp = ("FUTURO" in interp) or ("PASSADO" in interp)

            return rule_fp, interp_fp

        rule_fp, interp_fp = _check_line(gr, gi)
        if interp_fp and not rule_fp:
            gi = re.sub(r"(?<![_&])(FUTURO|PASSADO)", "", gi)
            gi = re.sub(r" +", " ", gi)
        elif rule_fp and not interp_fp:
            logger.debug(
                "Found FUTURO or PASSADO in GR but not GI, GR: `%s`, GI: `%s`", gr, gi
            )

        return (gr, gi)

    def _simplify_intensifiers(self, sentence):
        return sentence.replace("(++)", "(+)").replace("(--)", "(-)")

    def process(self, data):
        output = []

        for line in data:
            gr, gi = line

            for method in [
                self._fix_commas,
                self._fix_incorrect_directionals,
                self._fix_linebreaks,
                self._fix_misplaced_spaces,
                self._fix_punctuation,
                self._simplify_intensifiers,
            ]:
                gr, gi = (method(gr), method(gi))

                # One or both sentences empty, pair should be removed from set.
                if not gr or not gi:
                    break

            if gr and gi:
                gr, gi = self._remove_futuro_passado(gr, gi)
                output.append((gr, gi))

        return output


# Add element to the registry.
register_element(CleanupElement)
