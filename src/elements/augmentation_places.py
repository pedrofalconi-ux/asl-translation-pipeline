import os
import re
import csv
import random

from artifact import get_artifact_directory
from elements.element import PipelineElement
from registry import register_element


class PlaceAugmentation(PipelineElement):
    '''Data augmentation for places (cities, states and countries)
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
                '`place_augmentation` requires `path` and `max_new_sentences` parameter.')

    def process(self, data):
        list_places_gi = list()
        list_places_gr = list()
        # make list with all places passed  by args (path)
        # these lists will be used by generate method to make augmentation for each place
        for item in self._reader:
            list_places_gr.append(item[0])
            list_places_gi.append(item[1])

        # data augmentation generated
        data_augmentation = self.generate(data, list_places_gr, list_places_gi)
        # set to list * you can't concat set + list
        data_augmentation = list(data_augmentation)
        random.shuffle(data_augmentation)
        data = data + data_augmentation[:self._max_new_sentences]
        return data

    def generate(self, corpus_sample, list_places_gr, list_places_gi):
        data = set()
        for row_gr, row_gi in corpus_sample:
            # looking for places on the row
            # e.g Viajei para Recife ontem., VIAJAR RECIFE&CIDADE ONTEM [PONTO]
            # literals expect to receive "Recife" and "RECIFE & CIDADE"
            literals = self.row_search(
                row_gr, row_gi, list_places_gr, list_places_gi)

            for (literal_gr, literal_gi) in literals:
                occurrences = (re.findall(literal_gr, row_gr), re.findall(
                    literal_gi, row_gi))
                # if exists more than one occurrence ignore line to avoid incorrect replaces
                # e.g Viejei para Natal no Natal, VIAJAR NATAL no NATAL&CIDADE
                if len(occurrences[0]) == 1 and len(occurrences[1]) == 1:
                    # make sentences with all places except  the place found on current line
                    list_gr = [re.sub(literal_gr, place, row_gr)
                               for place in list_places_gr if literal_gr != place]
                    list_gi = [re.sub(literal_gi, place, row_gi)
                               for place in list_places_gi if literal_gi != place]
                    for element_gr, element_gi in zip(list_gr, list_gi):
                        data.add((element_gr, element_gi))
        # return a new set with elements in the set that are not in the others
        return data.difference(corpus_sample)

    def row_search(self, row_gr, row_gi, list_gr, list_gi):
        _list = list()
        words_gr = row_gr.split()
        words_gi = row_gi.split()

        for item_gr, item_gi in zip(list_gr, list_gi):
            # check if exists a place  (on current line) in the list of places already read
            if item_gr in words_gr and item_gi in words_gi:
                _list.append((item_gr, item_gi))
        return _list

    def __del__(self):
        if self._fd:
            self._fd.close()


# Add element to the registry
register_element(PlaceAugmentation)
