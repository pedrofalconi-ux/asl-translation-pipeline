import os
import re
import csv
import random
import itertools

from artifact import get_artifact_directory
from elements.element import PipelineElement
from registry import register_element
from utils import resolve_relative_path

REGEX_LATIN = 'A-ZÁÉÍÓÚÀÂÊÔÃÕÜÇa-záéíóúàâêôãõüç'

class NegationAugmentation(PipelineElement):
    '''Data augmentation for Negation
    '''
    name = 'negation_augmentation'
    version = 2

    _fd = None
    _reader = None
    _path = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        try:
            max_new_sentences = int(kwargs['max_new_sentences']) if 'max_new_sentences' in kwargs else 0
            self._max_new_sentences = max_new_sentences if max_new_sentences else None
            self._path = resolve_relative_path(kwargs['path'])
            self._fd = open(self._path, 'r')
            self._reader = csv.reader(self._fd)
        except KeyError:
            raise ValueError(
                '`negation_augmentation` requires `path` and `sample` parameter.')

    def process(self, data):
        list_negation = {}

        #path = 'negacao.csv'
        #fd = open(path, 'r', encoding='utf8')
        #reader = csv.reader(fd)

        for item in self._reader:
            list_negation[item[0]] = ''   #insets every word in the list of negation in "list_negation"
            list_negation[item[0][4:]] = ''   #insert the non-negated word in the list

        # fetching_expression = fetching_expression[:-1]  #removes the last "or (|)"
        # fetching_expression += ")"  #ends the expression
        # re_fetch = r"" + fetching_expression

        data_augmentation = set()   #creates a set in which to add the augmented sentences

        #goes over every line and makes that augmentation for that line, concatenating the results in "data_augmentation"
        for i in data:
            batch_generated = self.generate(list_negation, i)    #generate the new sentences
            random.shuffle(batch_generated)

            #add every new sentence to the data_augmentation set in order to avoid repeated sentences
            for augmented_sentence in batch_generated[:self._max_new_sentences]:
                data_augmentation.add(augmented_sentence)

        #shuffles the augmented sentences and then concatenates that first sentences (number given by value "sample") with the original data
        data_augmentation = list(data_augmentation) #turns the set into a list to be used for the shuffel and concatenation
        random.shuffle(data_augmentation)
        data = data + data_augmentation

        return data #returns the original data along with its augmented version

    def generate(self, list_negation, line):
        """[This method takes a line and checks if any word in it is inside a given list of
        words with negation, if there are no words it returns nothing, but if there is one
        word it returns a version of it, but with the word negated, e.g, "EU SER ISSO" must
        return itself and "EU NÃO_SER ISSO".
        In case there is more than one word in the sentence that is in the list then it must
        return all possible combinations of the phrase with the words normally or negated,
        e.g, the sentece "EU SER ISSO AQUI" must become the following sentences:
        "EU NÃO_SER ISSO AQUI", "EU SER ISSO NÃO_AQUI" and "EU NÃO_SER ISSO NÃO_AQUI]

        Arguments:
            list_negation {[dictionary]} -- [dictionary with all the words in both negated and non-negated forms]
            line {[tuple of strings]} -- [tuple of two strings: "gr" and "gi", which representing the same sentence in different forms]

        Returns:
            [list of tuples] -- [Return a list of tuples with the "gr" and "gi" version of the sentence, which tuple being one augmented sentence]
        """

        lista = []  #list where all the generated augmentations will be put

        words_found_gr = []    #list where all the words that are both in the "gr" part of sentence and in the list of negated words will be put
        words_found_gi = []    #list where all the words that are both in the "gi" part of  sentence and in the list of negated words will be put

        words_gr = line[0].split()  #splits the "gr" sentence into words in order to check if they are in the list
        words_gi = line[1].split()  #splits the "gi" sentence into words in order to check if they are in the list
        previous_word = ''

        #goes over every words of both "gr" and "gi" sentences
        for item_gr in words_gr:
            #checks if the word in "gr" is in the list of negation
            if previous_word == 'NÃO':  #if preceded by "NÃO" then it adds "NÃO" + white space + word to list of words found
                if 'NÃO_' + item_gr.upper() in list_negation or 'não_' + item_gr.lower() in list_negation:
                    words_found_gr.append('NÃO ' + item_gr.upper())
            else:
                if item_gr.upper() in list_negation or item_gr.lower() in list_negation:    #if not preceded by "NÃO", then onlythe word itself will be added
                        words_found_gr.append(item_gr.upper())
            previous_word = item_gr.upper() 
        for item_gi in words_gi:
                #checks if the word in "gi" is in the list of negation
                if item_gi.upper() in list_negation or item_gi.lower() in list_negation:
                    words_found_gi.append(item_gi.upper())

        if words_found_gr and words_found_gi and len(words_found_gr) == len(words_found_gi):
            number_of_words = len(words_found_gr)    #number of words that are in the list that were found in the sentence

            #if only one word was found then it returns the sentence negated
            if number_of_words == 1:

                if 'NÃO_' == words_found_gi[0][:4] and ('NÃO ' == words_found_gr[0][:4] or 'NÃO_' == words_found_gr[0][:4]):    #if the word is negated then returns the sentence with the non-negated word
                    word_without_negation = words_found_gi[0][4:]
                    new_aug = (re.sub(r'\b' + words_found_gr[0] + r'\b', word_without_negation, line[0]), re.sub(r'\b' + words_found_gi[0] + r'\b', word_without_negation, line[1]))
                    lista.append(new_aug)    #inserts the augmented sentence into the list

                elif 'NÃO_' != words_found_gi[0][:4] and 'NÃO ' != words_found_gr[0][:4] and 'NÃO_' != words_found_gr[0][:4]:    #if the word is non-negated then returns the sentence with the negated word
                    new_aug = (re.sub(r'(\b' + words_found_gr[0] + r'\b)', r'NÃO \1', line[0]), re.sub(r'(\b' + words_found_gi[0] + r'\b)', r'NÃO_\1', line[1]))
                    lista.append(new_aug)    #inserts the augmented sentence into the list


            #if more than one word was found then it returns all possible combinations of these words in the sentence (negated or not negated)
            else:

                list_of_words_caught_gr = []   #this list will be used to avoid repeating the original sentence in the augmentation for "gr"
                list_of_words_caught_gi = []   #this list will be used to avoid repeating the original sentence in the augmentation for "gi"

                #words_found_gi = [] #list to store what words from the list were originally in the sentence, this will needed in order to skip the case when the augmented sentence is the original sentence

                re_words_gr = []   #this list contains the regex expression for which word of the sentence that is in the list for "gr"
                re_words_gi = []   #this list contains the regex expression for which word of the sentence that is in the list for "gi"

                #generates a regex expression just for the words found and puts the word itself and a negated version of it in "list_of_words_caught" (replacing what was in it before) for every word found
                for index, word_gi in enumerate(set(words_found_gi)):  #"words_found_gr/gi" is made into a set to eliminate repeated words

                    if word_gi[:4].upper() == 'NÃO_':  #in case the world is already negated then it'll add the negated word along a non-negated version of it in the "gi"
                        re_words_gi.append(r'\b(' + word_gi.upper() + '|' + word_gi[4:].upper() + r')\b')    #regex expression for both the negated and non-negated word
                        list_of_words_caught_gi.append([word_gi.upper()]) #inserts a list with the negated word as its first element
                        list_of_words_caught_gi[index].append(word_gi[4:].upper())    #adds the non-negated word as its second element in the list for that word

                    else:   #in case the word is non-negated in the "gi"
                        re_words_gi.append(r'\b(' + word_gi.upper() + '|' + 'NÃO_' + word_gi.upper() + r')\b')    #regex expression for the non-negated word
                        list_of_words_caught_gi.append([word_gi.upper()]) #inserts a list with the original word as its first element
                        list_of_words_caught_gi[index].append('NÃO_' + word_gi.upper())    #adds the negated word as its second element in the list for that word
                
                
                #generates a regex expression just for the words found and puts the word itself and a negated version of it in "list_of_words_caught" (replacing what was in it before) for every word found
                for index, word_gr in enumerate(set(words_found_gr)):
                    if word_gr[:4].upper() == 'NÃO_' or word_gr[:4].upper() == 'NÃO ':  # if the words comes negated
                        re_words_gr.append(r'\b(' + word_gr.upper() + '|' + word_gr[4:].upper() + '|' + 'NÃO ' + word_gr[4:].upper() + r')\b') 
                        list_of_words_caught_gr.append([word_gr.upper()]) #inserts a list with the negated word as its first element
                        list_of_words_caught_gr[index].append(word_gr[4:].upper())    #adds the non-negated word as its second element in the list for that word

                    else:   # if the words comes without negation
                        re_words_gr.append(r'\b(' + word_gr.upper() + '|' + 'NÃO_' + word_gr.upper() + '|' + 'NÃO ' + word_gr.upper() + r')\b')    #regex expression for the non-negated word
                        list_of_words_caught_gr.append([word_gr.upper()]) #inserts a list with the original word as its first element
                        list_of_words_caught_gr[index].append('NÃO_' + word_gr.upper())    #adds the negated word as its second element in the list for that word

                #makes all possible combinations of the word and their negated versions from "words_found_gi"
                #as an example, from "EU SER ISSO AQUI" will be created the possibilities: [(SER, AQUI), (NÃO_SER, AQUI), (SER, NÃO_AQUI), (NÃO_SER, NÃO_AQUI)]
                combinations_iterator_gr = itertools.product(*list_of_words_caught_gr)
                combinations_iterator_gi = itertools.product(*list_of_words_caught_gi)

                #dividing the sentence into "gr" and "gi"
                sentence_gr = line[0]
                sentence_gi = line[1]

                next(combinations_iterator_gr)  #this next is necessary in order to skip the first combination, i.e, the original sentence
                next(combinations_iterator_gi)  #this next is necessary in order to skip the first combination, i.e, the original sentence

                combinations_gr = [i for i in combinations_iterator_gr] # creates a list from the combinations
                random.shuffle(combinations_gr) # shuffles the list in order to not generate the sentences in a specific order
                combinations_gr = combinations_gr[:self._max_new_sentences] # only generate the correct number of sentences from the number of combinations

                combinations_gi = [i for i in combinations_iterator_gi] # creates a list from the combinations
                random.shuffle(combinations_gi) # shuffles the list in order to not generate the sentences in a specific order
                combinations_gi = combinations_gi[:self._max_new_sentences] # only generate the correct number of sentences from the number of combinations

                #for every possible combination it generates an augmented version of the original sentence
                for words_gr, words_gi in zip(combinations_gr, combinations_gi):
                    #goes over every word of the possibility (named "words" in the loop for combinations)
                    i = 0
                    for word_gr, word_gi in zip(words_gr, words_gi):
                        sentence_gr = re.sub(re_words_gr[i], word_gr, sentence_gr)    #makes the right replacement for which word in "gr"
                        sentence_gi = re.sub(re_words_gi[i], word_gi, sentence_gi)    #makes the right replacement for which word in "gi"
                        i += 1

                    lista.append((sentence_gr, sentence_gi))    #inserts the augmented sentence into the list

        return lista    #returns the list, whether empty (no augmentation possible) or with the augmentations

    def __del__(self):
        if self._fd:
            self._fd.close()


# Add element to the registry
register_element(NegationAugmentation)
