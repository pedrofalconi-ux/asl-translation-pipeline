import csv
import logging
import random
import re
from itertools import product

from elements.element import PipelineElement
from registry import register_element
from utils import resolve_relative_path

logger = logging.getLogger(__name__)

REGEX_LATIN = "A-ZÁÉÍÓÚÀÂÊÔÃÕÜÇa-záéíóúàâêôãõüç"


class IntensidadeAugmentation(PipelineElement):
    """Data augmentation for Intensifier
    Arguments:
        PipelineElement {[type]} -- [description]
    Keyword Arguments:
        sample {int} -- [description] (default: {0})
    Raises:
        ValueError: [description]
    Returns:
        [type] -- [description]
    """

    name = "intensidade_augmentation"
    version = 2

    _intensifiers = {
        "(+)": [
            "EXTREMAMENTE",
            "MUITÍSSIMO",
            "DEMASIADO",
            "MAIS",
            "MUITO",
            "BASTANTE",
            "DEMAIS",
            "TAO",
            "TÃO",
        ],
        "(-)": ["MENOS", "POUCO", "POUQUISSIMO"],
        "": "",
    }
    # Reestruturando intensifiers para uso no augmentation
    _intensifiers_words = []
    _structured_intensifiers = {}
    for key, values in _intensifiers.items():
        for value in values:
            _structured_intensifiers[value] = key
            _intensifiers_words.append(value)
    _augment_data = set()
    _intensifiers_sub = "!!!"  # marcador de intensificador na frase

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        try:
            # this is slice index thus the None as default value
            max_new_sentences = (
                int(kwargs["max_new_sentences"]) if "max_new_sentences" in kwargs else 0
            )
            intensifiers_list_path = resolve_relative_path(kwargs["path"])
            self._max_new_sentences = max_new_sentences if max_new_sentences else None
            with open(intensifiers_list_path, encoding="utf8") as f:
                self._list_intesifiers = {item.strip() for item in f}
        except KeyError:
            raise ValueError("`intensidade_augmentation` requires `path` parameter.")

    def _remove_intensifiers(self, gr, gi):
        """
        Remove intensificadores de GR e GI, e muda o intensificador de GR
        para um simbolo pre-definido a fim de indentificar a posicao do
        itensificador
        Arguments:
            data {list} -- lista de tuplas com gr e gi
        Returns:
            list -- list de tuplas de data modificadas
        """
        splited_gr = gr.split()

        for index, word in enumerate(gr.split()):
            if word in self._list_intesifiers:
                if splited_gr[index - 1] in self._structured_intensifiers and index > 0:
                    splited_gr[index - 1] = self._intensifiers_sub
                else:
                    if splited_gr[index + 1] in self._structured_intensifiers:
                        splited_gr[index + 1] = self._intensifiers_sub

        replaced_gr = " ".join(splited_gr)
        replaced_gi = re.sub(r"\([+-]+\)", self._intensifiers_sub, gi)

        return replaced_gr, replaced_gi

    def _augment(self, replaced_gr, replaced_gi):
        """Gera para cada linha de GR e GI as combinações com os intensificadores
        de acordo com as palavras aumentaveis na frase
        Arguments:
            augmentables {list} -- lista de palavras insenfificaveis encontrada na frase
            gr {string} -- Frases com intensificadores por extenso (MUITO, POUCO, ...)
            gi {string} -- Frases com intesificadores com sinais (+, -)
        """
        augmented_phrase = []
        gr, gi = replaced_gr, replaced_gi
        intensifiers_combinations = product(
            self._intensifiers_words, repeat=len(re.findall(r"\!\!\!", gr))
        )
        intensifiers_combinations_list = [i for i in intensifiers_combinations]
        random.shuffle(intensifiers_combinations_list)
        intensifiers_combinations_list = intensifiers_combinations_list[
            : self._max_new_sentences
        ]

        for line_comb in intensifiers_combinations_list:

            gr_for_aug, gi_for_aug = gr, gi

            for word_comb in line_comb:
                gr_for_aug = gr_for_aug.replace(self._intensifiers_sub, word_comb, 1)
                gi_for_aug = gi_for_aug.replace(
                    self._intensifiers_sub, self._structured_intensifiers[word_comb], 1
                )

            augmented_phrase.append((gr_for_aug, gi_for_aug))

        return augmented_phrase

    def process(self, data):
        """Funcao de entrada, que executa as outras da classe
        Arguments:
            data {list} -- data contendo gr e gi
        Returns:
            [list] -- data com o augment concluido]
        """

        augmented_phrases = []
        wrong_sentences = []
        for gr, gi in data:
            try:
                if re.search(r"\([+-]+\)", gi):
                    replaced_gr, replaced_gi = self._remove_intensifiers(gr, gi)

                    if len(re.findall(self._intensifiers_sub, replaced_gr)) == len(
                        re.findall(self._intensifiers_sub, replaced_gi)
                    ):
                        augmented_phrases.extend(self._augment(replaced_gr, replaced_gi))
                    elif (
                        len(re.findall(self._intensifiers_sub, replaced_gi)) >= 1
                        or len(re.findall(self._intensifiers_sub, replaced_gr)) >= 1
                    ):
                        wrong_sentences.append((gr, gi))
            except:
                logger.error("Could not augment tuple, skipping...")
                continue

        random.shuffle(augmented_phrases)
        data.extend(augmented_phrases)

        return data


register_element(IntensidadeAugmentation)
