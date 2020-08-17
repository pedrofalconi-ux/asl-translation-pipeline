import re
import random
import csv
from elements.element import PipelineElement
from registry import register_element
import logging


logger = logging.getLogger(__name__)

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
    _intensifiers = {
        "(+)": [
            "EXTREMAMENTE",
            "MUITÍSSIMO",
            "DEMASIADO",
            "MAIS",
            "MUITO",
            "BASTANTE",
            "DEMAIS",
        ],
        "(-)": ["MENOS", "POUCO", "POUQUISSIMO"],
        "": "",
    }
    # Reestruturando intensifiers para uso no augmentation
    _structured_intensifiers = {}
    for key, values in _intensifiers.items():
        for value in values:
            _structured_intensifiers[value] = key
    _augment_data = set()
    _intensifiers_sub = "!!!"  # marcador de intensificador na frase

    def __init__(self, intensifiers_list_path, *args, **kwargs):
        super().__init__(*args, **kwargs)
        try:
            # this is slice index thus the None as default value
            max_new_sentences = int(kwargs['max_new_sentences']) if 'max_new_sentences' in kwargs else 0
            self._max_new_sentences = max_new_sentences if max_new_sentences else None
            with open(intensifiers_list_path, encoding="utf8") as f:
                self._list_intesifiers = {item.strip() for item in f}
        except KeyError:
            raise ValueError(
                "`intensidade_augmentation` requires `path` parameter."
            )

    def _remove_intensifiers(self, data):
        """
        Remove intensificadores de GR e GI, e muda o intensificador de GR
        para um simbolo pre-definido a fim de indentificar a posicao do 
        itensificador
        Arguments:
            data {list} -- lista de tuplas com gr e gi
        Returns:
            list -- list de tuplas de data modificadas
        """
        phrase_wout_intensifiers = []
        for line in data:
            gr_line, gi_line = line
            for key in self._structured_intensifiers:
                gr_line = gr_line.replace(key, self._intensifiers_sub)
                gi_line = gi_line.replace(
                    self._structured_intensifiers[key], "")
            phrase_wout_intensifiers.append((gr_line, gi_line))
        return phrase_wout_intensifiers

    def _find_augmentables(self, gr, gi, list_intesifiers):
        """Lista todas as palavras aumentaveis na frase
        Arguments:
            gr {string} -- Frases com intensificadores por extenso (MUITO, POUCO, ...)
            gi {string} -- Frases com intesificadores com sinais (+,-)
            list_intesifiers {dict} -- Palavras intensificaveis
        Returns:
            list -- lista com as palavras intensificaveis encontradas em gr e gi
        """
        augmentables_found = []
        for word in gi.split():
            if word in list_intesifiers and word in gr:
                augmentables_found.append(word)
        return augmentables_found

    def _augment(self, augmentables, gr, gi):
        """Gera para cada linha de GR e GI as combinações com os intensificadores 
        de acordo com as palavras aumentaveis na frase
        Arguments:
            augmentables {list} -- lista de palavras insenfificaveis encontrada na frase
            gr {string} -- Frases com intensificadores por extenso (MUITO, POUCO, ...)
            gi {string} -- Frases com intesificadores com sinais (+, -)
        """
        temp = gr, gi
        for item in self._structured_intensifiers:
            for word in augmentables:
                prefix = f"{self._intensifiers_sub} {word}"
                posfix = f"{word} {self._intensifiers_sub}"
                # As expressoes abaixo definirao a frase a ser gerada com base na palavra aumentavel na frase
                # e na posicao  que o identificador de aumentavel se encontra
                if re.search(prefix, temp[0]):
                    temp = (
                        re.sub(prefix, f"{item} {word}", temp[0]),
                        re.sub(
                            f"{word}(\([+-]\))*",
                            f"{word}{self._structured_intensifiers[item]}",
                            temp[1],
                        ),
                    )
                    self._augment(augmentables[-1:], temp[0], temp[1])
                elif re.search(posfix, temp[0]):
                    temp = (
                        re.sub(posfix, f"{word} {item}", temp[0]),
                        re.sub(
                            f"{word}(\([+-]\))*",
                            f"{word}{self._structured_intensifiers[item]}",
                            temp[1],
                        ),
                    )
                    self._augment(augmentables[-1:], temp[0], temp[1])
                else:
                    self._augment_data.add(temp)
                    return
            temp = gr, gi

    def process(self, data):
        """Funcao de entrada, que executa as outras da classe
        Arguments:
            data {list} -- data contendo gr e gi
        Returns:
            [list] -- data com o augment concluido
        """
        data_wout_intensifiers = self._remove_intensifiers(data)
        augmented_lines = list()
        data = list(data)
   
        # TODO remover final_augment,
        for line in data_wout_intensifiers:
            gr, gi = line
            augmentables_found = self._find_augmentables(
                gr, gi, self._list_intesifiers)
            self._augment(augmentables_found, gr, gi)
            augmented_lines.extend(self._augment_data)
            self._augment_data.clear()
        random.shuffle(augmented_lines)
        
        # Remove orginal data for avoid duplicates data in corpus
        try:
            augmented_lines.remove(data[0])
        except Exception as e:
            pass
        augmented_lines = augmented_lines[:self._max_new_sentences]

        data.extend(augmented_lines)

        return data

register_element(IntensidadeAugmentation)
