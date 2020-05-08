import csv
import random
import re

from artifact import get_artifact_directory
from elements.element import PipelineElement
from registry import register_element


class FamososAugmentation(PipelineElement):
    '''Data augmentation for famous people.'''
    name = 'famosos_augmentation'

    _fd = None
    _path = None
    _max_new_sentences = 0
    _count = 0

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        try:
            self._max_new_sentences = int(kwargs['max_new_sentences'])
            self._path = kwargs['path']
            self._fd = open(self._path, 'r')
        except KeyError:
            raise ValueError(
                '`famosos_augmentation` requires `path` and `sample` parameter.')

    def process(self, data):
        famosos_gr = list()
        famosos_gi = list()

        for item in data:
            famosos_gr.append(item[0])  # the names for the 'gr' are put in a list that will be looped over to make the augmentation
            famosos_gi.append(item[1])  # the names for the 'gi' are put in a list that will be looped over to make the augmentation

        combined_gr = ''    # regex expression that will be used to get the names of the list in which sentence for the 'gr'
        combined_gi = ''    # regex expression that will be used to get the names of the list in which sentence for the 'gi'
        match_famoso_gr = {}    # dictionary containing the name of the famous people as the key and its 'gr' regex expression as the value
        match_famoso_gi = {}    # dictionary containing the name of the famous people as the key and its 'gi' regex expression as the value

        # goes over every name in the list to put them in the regex expressions and dictionaries
        for (famoso_gr, famoso_gi) in list(zip(famosos_gr, famosos_gi)):
            lista_gr = famoso_gr.split(' ') # turns the full name into a list of name and surnames for the 'gr'
            lista_gi = famoso_gi.split('_') # turns the full name into a list of name and surnames for the 'gi'
            match_famoso_gr[famoso_gr] = ''
            match_famoso_gi[famoso_gi] = ''
            combined_gr += '('
            combined_gi += '('

            # goes over every name of the famous person (except the last one) to create the regex expression and dictionary value for 'gr'
            for i in range(0, len(lista_gr) - 1):
                combined_gr += r'(\\b' + (lista_gr[i]) + r'\\b)(\s|_)'
                match_famoso_gr[famoso_gr] += r'(\\b' + (lista_gr[i]) + r'\\b)?(\s|_)?'

            # goes over every name of the famous person (except the last one) to create the regex expression and dictionary value for 'gi'
            for j in range(0, len(lista_gi) - 1):
                combined_gi += '(' + (lista_gi[j]) + '_)'
                match_famoso_gi[famoso_gi] += '(' + (lista_gi[j]) + '_)?'

            combined_gr += r'(\\b' + (''.join(lista_gr[-1:])) + r'\\b))|'    # puts the last name in the expression for 'gr' with an 'or (|)' at the end so that the following names will also be caught
            match_famoso_gr[famoso_gr] += r'(\\b' + (''.join(lista_gr[-1:])) + r'\\b)'    # puts the last name in the dictionary value for 'gr'
            match_famoso_gr[famoso_gr] = r'' + match_famoso_gr[famoso_gr]

            combined_gi += '' + (''.join(lista_gi[-1:])) + ')|'    # puts the last name in the expression for 'gi' with an 'or (|)' at the end so that the following names will also be caught
            match_famoso_gi[famoso_gi] += '((' + (''.join(lista_gi[-1:])) + '))'    # puts the last name in the dictionary value for 'gi'
            match_famoso_gi[famoso_gi] = r'' + match_famoso_gi[famoso_gi]

        combined_gr = combined_gr[:-1]  # removes that last 'or (|)' of the expression for 'gr'
        re_gr = r'' + combined_gr
        combined_gi = combined_gi[:-1]  # removes that last 'or (|)' of the expression for 'gi'
        re_gi = r'' + combined_gi

        data_augmentation = set()

        # goes over every line and makes that augmentation for that line, concatenating the results in 'data_augmentation'
        for i in data:
            batch_generated = self.generate(i, re_gr, re_gi, famosos_gr, famosos_gi, match_famoso_gr, match_famoso_gi)

            # add every new sentence to the data_augmentation set in order to avoid repeated sentences
            for augmented_sentence in batch_generated:
                data_augmentation.add(augmented_sentence)

        # shuffles the augmented sentences and then concatenates that first sentences (number given by value 'sample') with the original data
        data_augmentation = list(data_augmentation) # turns the set into a list to be used for the shuffle and concatenation
        random.shuffle(data_augmentation)
        data = data + data_augmentation[:self._max_new_sentences]
        return data # returns the original data along with its augmented version

    def generate(self, line, re_gr, re_gi, famososExamples_gr, famososExamples_gi, dict_gr, dict_gi):
        '''[This method takes all occurences of words in the strings 'line_gr' and 'line_gi' that are in a list
        of famous and puts them in inside two lists (one for 'gr' and another for 'gi'), then it checks if the
        lists are the same size and aren't empty, i.e, if there are any occurences of a word of the list in the
        sentence. If any words are found the sentence is then augmented so the found words are changed for the
        other words of the list, returning then a list of the same sentence, but with different words in place
        of the ones that are in the list.]

        Arguments:
            line {[tuple of string]} -- [tuple of two strings: 'gr' and 'gi', which representing the same sentence in different forms]
            re_gr {[regex expression]} -- [expression with all the words in the list of famous people for the 'gr']
            re_gi {[regex expression]} -- [expression with all the words in the list of famous people for the 'gi']
            famososExamples_gr {[list of strings]} -- [list with the string of the name of the famous people in the list for the 'gr']
            famososExamples_gi {[list of strings]} -- [list with the string of the name of the famous people in the list for the 'gi']
            dict_gr {[dictionary]} -- [dictionary containing the name of the famous people as the key and its 'gr' regex expression as the value]
            dict_gi {[dictionary]} -- [dictionary containing the name of the famous people as the key and its 'gi' regex expression as the value]
        '''

        lista = list()
        line_gr = line[0]
        line_gi = line[1]

        # uses re_gr (the regex expression with all the words of the list) to check if there are any words in the sentence (both the 'gr' and 'gi' versions)
        # and then puts these words inside of a list
        occurences_gr = re.findall(re_gr, line_gr)
        occurences_gi = re.findall(re_gi, line_gi)

        # checks if any words were found and if the number of occurences of these words match in both the 'gr' and 'gi' side
        if occurences_gr and occurences_gi and len(occurences_gr) == len(occurences_gi):
            # loops every word of the original list in order to change the words of the original sentence that were in the list with the other words of the list
            for index, (famoso_gr, famoso_gi) in enumerate(list(zip(famososExamples_gr, famososExamples_gi))):
                # checks if the looped word is already in the original sentence, not making the augmentation in that case
                if re.search(dict_gr[famoso_gr], line_gr) == None and re.search(dict_gi[famoso_gi], line_gi) == None:
                    lista.append((re.sub(re_gr, famoso_gr, line_gr, 1), # inserts the augmented sentece in a list
                                  re.sub(re_gi, famoso_gi, line_gi, 1)))
            return lista    # returns the list of augmentations for that line

        return lista    # returns the list of augmentations for that line, this second return is for the case of no augmentation needed

    def __del__(self):
        if self._fd:
            self._fd.close()


# Add element to the registry.
register_element(FamososAugmentation)
