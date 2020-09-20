import os
import re
import csv
import random
from itertools import permutations

from artifact import get_artifact_directory
from elements.element import PipelineElement
from registry import register_element


class PlacesAugmentation(PipelineElement):
    '''Data augmentation for lugares
    '''
    name = 'place_augmentation'

    _fd = None
    _reader = None
    _path = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        try:
            max_new_sentences = int(kwargs['max_new_sentences']) if 'max_new_sentences' in kwargs else 0
            self._max_new_sentences = max_new_sentences if max_new_sentences else None
            self._path = kwargs['path']
            self._fd = open(self._path, 'r')
            self._reader = csv.reader(self._fd)
        except KeyError:
            raise ValueError(
                '`lugares_augmentation` requires `path` and `max_new_sentences` parameter.')

    def process(self, data):
        list_lugares = list()
        # leitura do arquivo de lugares
        for item in self._reader:
            list_lugares.append((item[0], item[1]))

        # data argummentation final gerado
        data_augmentation = self.generate(data, list_lugares)
        random.shuffle(data_augmentation)
        data = data + data_augmentation
        return data

    def generate(self, corpus_sample, list_lugares):
        data = set()
        # mascaramento para evitar substituicoes erradas
        wrapper = lambda place: place[:1] + '<mark>' + place[1:]
        unrwrapper = lambda place: place.replace('<mark>', '')

        for row_gr, row_gi in corpus_sample:
            # procura por nomes na linha tual baseada na lista de lugares `list_lugares`
            literals = self.row_search(row_gr, row_gi, list_lugares)
            if literals:
                # limita o numero de possibilidades caso exista mais de 3 lugares na mesma frase
                literals = literals if len(literals) <= 3 else random.sample(literals, 3)
                # verifica todas as opcoes possiveis de substituicao baseada na quantidade de literais encontrados
                # e.g CHEGAR ONTEM JAPÃO VIAJAR PARA CHINA
                # Temos 2 possibilidades de alteracoes JAPÃO e CHINA
                # Logo nossa lista de opcoes teremos tuplas com 2 elementos
                # eg. ((JAPÃO, JAPÃO&PAÍS), (CHINA,CHINA&PAÍS))
                ## ...
                # No caso temos 48 (lista de lugares), 2 (lugares encontrados na linha)
                # Calculando o total de possibilidades temos 48 x 47 = 2256 possibilidades
                perm = list(permutations(list_lugares, len(literals)))
                random.shuffle(perm)
                # Pegamos apenas uma amostra do total geral (caso _max_new_sentences for 0 todas as sentencas serao retornadas)
                sample = perm[:self._max_new_sentences]
                for _tuple in sample:
                    gr, gi = row_gr, row_gi
                    # Substitui os literais encontrados na linha pelos lugares que estao na lista
                    # Como podemos ter mais de um literal na mesma linha, so devemos adicionar a frase a nossa lista de augmentation
                    # quando toda linha for atualizada
                    for name, literal in zip(_tuple, literals):
                        gr = re.sub(literal[0], wrapper(name[0]), gr)
                        gi = re.sub(literal[1], wrapper(name[1]), gi)
                    data.add((unrwrapper(gr), unrwrapper(gi)))
        # garante que nenhuma frase gerada sera igual ao corpus de entrada
        return list(data.difference(corpus_sample))

    def row_search(self, row_gr, row_gi, list_lugares):
        _list = set()
        for item_gr, item_gi in list_lugares:
            # verifica se existe o nome na linha, caso existe deve conter o mesmo numero de aparicao no gr e gi
            # considerando que item_gr = CHINA e gi = CHINA&PAÍS temos:
            # e.g. CHINA  E GRANDE, CHINA&PAÍS GRANDE
            # len(gr) = 1 e len(gi) = 1
            # e.g. CHINA  E GRANDE, JAPÃO&PAÍS GRANDE
            # len(gr) = 1 e len(gi) = 0
            if len(re.findall(item_gr, row_gr)) >= 1 and len(re.findall(item_gr, row_gr)) == len(re.findall(item_gi, row_gi)):
                _list.add((item_gr, item_gi))
        return list(_list)

    def __del__(self):
        if self._fd:
            self._fd.close()


# Add element to the registry
register_element(PlacesAugmentation)