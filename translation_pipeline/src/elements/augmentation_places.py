import os
import re
import csv
import random
from itertools import product

from artifact import get_artifact_directory
from elements.element import PipelineElement
from registry import register_element
from utils import resolve_relative_path

valid_chars = "A-ZÁÉÍÓÚÀÂÊÔÃÕÜÇa-záéíóúàâêôãõüç"

class PlacesAugmentation(PipelineElement):
    '''Data augmentation for lugares
    '''
    name = 'place_augmentation'
    not_phrases = set()

    _fd = None
    _reader = None
    _path = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        try:
            max_new_sentences = int(kwargs['max_new_sentences']) if 'max_new_sentences' in kwargs else 0
            new_places_total = int(kwargs['total_places']) if 'total_places' in kwargs else 3
            self._new_places_total = new_places_total if new_places_total else None
            self._max_new_sentences = max_new_sentences if max_new_sentences else None
            self._path = resolve_relative_path(kwargs['path'])
            self._fd = open(self._path, 'r')
            self._reader = csv.reader(self._fd)
        except KeyError:
            raise ValueError(
                '`lugares_augmentation` requires `path` and `max_new_sentences` parameter.')

    def process(self, data):
        aug_data = list()    # the function will return a list with all augmented places

        list_places = {} # dictionary with the lists for each type of place: Country, State and City
        countries = []  # list with every place that is a country (has the '&PAÍS' identifier) found in the 'lugares.csv' file
        states = []  # list with every place that is a states (has the '&ESTADO' identifier) found in the 'lugares.csv' file
        cities = []  # list with every place that is a city (has the '&CIDADE' identifier) found in the 'lugares.csv' file

        for row in self._reader:  # goes through each place of the 'lugares.csv' file, checking what type of place it is by its identifier, and putting it in the correct list
            if re.search('PAÍS',row[1]):
                countries.append(row[1])
            elif re.search('ESTADO',row[1]):
                states.append(row[1])
            elif re.search('CIDADE',row[1]):
                cities.append(row[1])

        list_places['PAÍS'] = countries # inserts the list of countries into the dictionary
        list_places['ESTADO'] = states # inserts the list of states into the dictionary
        list_places['CIDADE'] = cities # inserts the list of cities into the dictionary

        for phrase in data: # Generate the augmentation for each sentence of the corpus, adding them to a set
            aug_phrases = self.generate(phrase, list_places, self._max_new_sentences, self._new_places_total)
            aug_phrases_list = list(aug_phrases)
            for aug_phrase in aug_phrases_list:
                aug_data.append(aug_phrase)

        random.shuffle(aug_data)
        pattern = rf'[A-ZÁÉÍÓÚÀÂÊÔÃÕÜÇa-záéíóúàâêôãõüç_]+(?=&ESTADO|&PAÍS|&CIDADE)'
        
        data = data + list(aug_data)    # concatenates the original data with the augmented data (turned into a list)
        return data          

    def generate(self, data, places, max_new_sentences, max_num_places):
        augmented_phrases = set()
        gr, gi = data   # separates gr and gi in the sentence

        # Searches for places in the sentence, storing the names in one list, the types in another and the gi pattern in another
        gr_places_found, gi_places_found, gi_pattern = self.row_search(gr,gi,places)
        
        gr_places_found = gr_places_found[:max_num_places]
        gi_places_found = gi_places_found[:max_num_places]
        gi_pattern = gi_pattern[:max_num_places]

        splited_gr = self.split_phrase(gr, gr_places_found)  # splits the gr of the sentence into multiple sentences with one place in each
        splited_gi = self.split_phrase(gi,gi_pattern)      # splits the gi of the sentence into multiple sentences with one place in each

        # Creates all combinations of the places from the 'lugares.csv' file with their respective categories
        
        found_places = [places[i] for i in gi_places_found]
        s = product(*found_places)
        possible_places = list(s)   # makes the combinations into a list
        random.shuffle(possible_places) # shuffles the combinations in order to not always create the same structures
        possible_places = [k for k in possible_places if len(k) == len(set(k))][:max_new_sentences] # removes repeated cases (e.g ('BRASIL', 'BRASIL')) and only takes the specified amount of combinations

        if len(possible_places[0]) >= 1 and len(splited_gr) == len(splited_gi): # will only do the augmentation in case the element is not empty, i.e, there actually are places found in the sentence
            for places_comb in possible_places:    # goes through every possible combination, which will be substitute the original places in the sentence
                new_phrase_gr = [] # The new gr sentence generated
                new_phrase_gi = [] # The new gi sentence generated

                count = 0   # counts the number of times it loops through the partitioned sentence

                for pattern_gr, pattern_gi, item, part_gr, part_gi in zip(gr_places_found, gi_places_found, places_comb, splited_gr, splited_gi):
                    # each place in the sentence will be replaced by one of the combinations
                    pattern_gr = r'\b' + pattern_gr + r'\b'
                    pattern_gi = r'\b' + pattern_gi + r'\b'
                    
                    ex = re.search(fr'([{valid_chars}_])+(?=&PAÍS|&ESTADO|&CIDADE)',item).group(0) # searches for all the places found and puts the in a list (e.g "EU AMAR BRASIL&PAÍS" returns just "BRASIL")
                    
                    new_phrase_gr.append(re.sub(pattern_gr, ex, part_gr)) # makes the replacement of the nth place in the sentence in the nth partitioned sentence for the 'gr'
                    new_phrase_gi.append(re.sub(pattern_gr+'&'+pattern_gi, item, part_gi)) # makes the replacement of the nth place in the sentence in the nth partitioned sentence for the 'gi'

                    count += 1

                # inserts the end of the original sentence (without augmentable place) in the augmented sentence in case it didn't loop through all the partitions
                if count < len(splited_gr):
                    new_phrase_gr.append(splited_gr[-1])
                    new_phrase_gi.append(splited_gi[-1])

                augmented_phrases.add((''.join(new_phrase_gr), ''.join(new_phrase_gi)))   # concatenates the split augmented sentences into one sentence, like the original, but with the correct replacements

        try:    # if the original sentence is found in the set of augmented sentences, then it's removed
            augmented_phrases.remove((gr, gi))
            return augmented_phrases
        except: # otherwise the function will just return the augmented sentences
            return augmented_phrases

    def correspondence_aval(self, sentences, pattern):
        for gr, gi in sentences:

            places_gi = [word.replace('_', ' ') for word in re.findall(pattern, gi)]
            places_gr = list(filter(lambda word: word in gr, places_gi))

            if not places_gr == places_gi:
                print(f'\nGR: {gr}\nplaces found in GR: {places_gr}\n\nGI: {gi}\nplaces found in GI: {places_gi}')

    def row_search(self, gr,gi,places):
        """Searches the sentence for the places that are given in the `lugares.csv` file
        and stores them in lists.

        Args:
            gr (string): The `gr` version of the sentence
            gi (string): The `gi` version of the sentence
            places (dict): Dictionary with lists of places for each type of place

        Returns:
            tuple: Returns the list of places found, the list of types of places according the the places found and the `gi` pattern for each place found
        """
        pattern =fr'([{valid_chars}_]+&(PAÍS|ESTADO|CIDADE))'
        gr_places_found = []    # stores the cities/states/countries found in the sentence
        gi_places_found = []    # stores the type of places found in the sentence (city, state or country) according to the places found (same order)
                                # e.g "SOU DE MANAUS NO AMAZONAS/SOU MANAUS&CIDADE EM AMAZONAS&ESTADO", would create the lists ('MANAUS', 'AMAZONAS')
                                # and ('CIDADE', 'ESTADO')

        gi_pattern = []         #stores the patterns that will be used to replace the places in the 'gi'

        for place in re.findall(pattern,gi):  # for each place found the place itself, the type of place and the gi pattern will be stored for it
            place_split = place[0].split('&')
            if place_split[0]+'&'+place_split[1] in places['PAÍS'] \
                or place_split[0]+'&'+place_split[1] in places['ESTADO'] \
                or place_split[0]+'&'+place_split[1] in places['CIDADE']:
                gr_places_found.append(place_split[0])
                gi_places_found.append(place_split[1])
                gi_pattern.append(place_split[0]+'&'+place_split[1])

        return gr_places_found, gi_places_found, gi_pattern

    def split_phrase(self, phrase,patterns):
        """splits phrases by place, divinding one sentence into multiple sentences with one place in each.
        If the sentence has only one place, it will return a list with only the original sentence.

        Args:
            phrase (string): The phrase that will be splitted
            pattern (list of strings): List with the places that will be used to split the sentence

        Returns:
            list of strings: Returns the list with each each part of the sentence that has a place in it
        """
        phrases = list()
        
        for index, pattern in enumerate(patterns):
            new_phrase = phrase.split(pattern, 1)
            try:    # if the split was made, then concatenates the first splitted sentence into the list
                phrase = new_phrase[1]
                phrases.append(new_phrase[0] + pattern)
                if index == len(patterns) - 1:  # concatenates the end of the sentence, which doesn't include one of the places to augment
                    phrases.append(new_phrase[1])
            except: # if the split wasn't made (at the end of the sentence), then it inserts the end the sentence into the list
                phrase = new_phrase[0]
                phrases.append(new_phrase[0])

        return phrases

    def __del__(self):
        if self._fd:
            self._fd.close()


# Add element to the registry
register_element(PlacesAugmentation)
