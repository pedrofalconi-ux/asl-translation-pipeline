import csv
import os
import random
import re
from itertools import permutations

from artifact import get_artifact_directory
from elements.element import PipelineElement
from registry import register_element
from utils import resolve_relative_path


class FamososAugmentation(PipelineElement):
    """Data augmentation for famosos"""

    name = "famosos_augmentation"

    _fd = None
    _reader = None
    _path = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        try:
            max_new_sentences = (
                int(kwargs["max_new_sentences"]) if "max_new_sentences" in kwargs else 0
            )
            self._max_new_sentences = max_new_sentences if max_new_sentences else None
            self._path = resolve_relative_path(kwargs["path"])
            self._fd = open(self._path, "r")
            self._reader = csv.reader(self._fd)
        except KeyError:
            raise ValueError(
                "`famosos_augmentation` requires `path` and `max_new_sentences` parameter."
            )

    def process(self, data):
        list_famosos = list()
        # leitura do arquivo de famosos
        for item in self._reader:
            list_famosos.append((item[0], item[1]))

        # data argummentation final gerado
        data_augmentation = self.generate(data, list_famosos)
        random.shuffle(data_augmentation)
        data = data + data_augmentation
        return data

    def generate(self, corpus_sample, list_famosos):
        data = set()
        # mascaramento para evitar substituicoes erradas
        wrapper = lambda name: name[:1] + "<mark>" + name[1:]
        unrwrapper = lambda name: name.replace("<mark>", "")

        for row_gr, row_gi in corpus_sample:
            # procura por nomes na linha tual baseada na lista de famosos `list_famosos`
            literals = self.row_search(row_gr, row_gi, list_famosos)
            if literals:
                # limita o numero de possibilidades caso exista mais de 3 lugares na mesma frase
                literals = (
                    literals if len(literals) <= 3 else random.sample(literals, 3)
                )
                # verifica todas as opcoes possiveis de substituicao baseada na quantidade de literais encontrados
                # e.g SERGIO MORO CONVERSOU COM JAIR BOLSONARO
                # Temos 2 possibilidades de alteracoes `SERGIO MORO` e `JAIR BOLSONARO`
                # Logo nossa lista de opcoes teremos tuplas com 2 elementos
                # eg. ((LUIZ EDUARDO RAMOS,LUIZ_EDUARDO_RAMOS&FAMOSO), (WAGNER MOURA,WAGNER_MOURA&FAMOSO))
                ## ...
                # No caso temos 54 (lista de famosos), 2 (famosos encontrados na linha)
                # Calculando o total de possibilidades temos 54 x 53 = 2862 possibilidades
                perm = list(permutations(list_famosos, len(literals)))
                random.shuffle(perm)
                # Pegamos apenas uma amostra do total geral (caso _max_new_sentences for 0 todas as sentencas serao retornadas)
                sample = perm[: self._max_new_sentences]
                for _tuple in sample:
                    gr, gi = row_gr, row_gi
                    # Substitui os literais encontrados na linha pelos famosos que estao na lista
                    # Como podemos ter mais de um literal na mesma linha, so devemos adicionar a frase a nossa lista de augmentation
                    # quando toda linha for atualizada
                    for name, literal in zip(_tuple, literals):
                        gr = re.sub(literal[0], wrapper(name[0]), gr)
                        gi = re.sub(literal[1], wrapper(name[1]), gi)
                    data.add((unrwrapper(gr), unrwrapper(gi)))
        # garante que nenhuma frase gerada sera igual ao corpus de entrada
        return list(data.difference(corpus_sample))

    def row_search(self, row_gr, row_gi, list_famosos):
        _list = set()
        for item_gr, item_gi in list_famosos:
            # verifica se existe o nome na linha, caso existe deve conter o mesmo numero de aparicao no gr e gi
            # considerando que item_gr = SERGIO MORO e gi = SERGIO_MORO&FAMOSO temos:
            # e.g. SERGIO MORO SAIU, SERGIO_MORO&FAMOSO SAIR
            # len(gr) = 1 e len(gi) = 1
            # e.g. SERGIO MORO SAIU, JAIR_BOLSONARO&FAMOSO SAIR
            # len(gr) = 1 e len(gi) = 0
            if len(re.findall(item_gr, row_gr)) >= 1 and len(
                re.findall(item_gr, row_gr)
            ) == len(re.findall(item_gi, row_gi)):
                _list.add((item_gr, item_gi))
        return _list

    def __del__(self):
        if self._fd:
            self._fd.close()


# Add element to the registry
register_element(FamososAugmentation)
