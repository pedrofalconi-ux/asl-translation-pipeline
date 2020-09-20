import os
import re
import csv
import random
import itertools

from artifact import get_artifact_directory
from elements.element import PipelineElement
from registry import register_element

class NegationAugmentation(PipelineElement):
    '''Data augmentation for Negation
    '''
    name = 'negation_augmentation'

    _fd = None
    _reader = None
    _path = None
    _count = 0

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

        words_found = []    #list where all the words that are both in the sentence and in the list of negated words will be put

        words_gr = line[0].split()  #splits the "gr" sentence into words in order to check if they are in the list
        words_gi = line[1].split()  #splits the "gi" sentence into words in order to check if they are in the list

        #goes over every words of both "gr" and "gi" sentences
        for item_gr, item_gi in zip(words_gr, words_gi):
                #checks if the word in both "gr" and "gi" are in the list of negation
                if item_gr in list_negation and item_gi in list_negation:
                    words_found.append(item_gr)

        #checks if there are any occurrences of words of the list in the sentence and if the number of occurrences match for "gr" and "gi"
        if words_found:
            number_of_words = len(words_found)    #number of words that are in the list that were found in the sentence

            #if only one word was found then it returns the sentence negated
            if number_of_words == 1:

                if 'NÃO_' == words_found[0][:4]:    #if the word is negated then returns the sentence with the non-negated word
                    word_without_negation = words_found[0][4:]
                    lista.append((re.sub(r'\b' + words_found[0] + r'\b', word_without_negation, line[0]), re.sub(r'\b' + words_found[0] + r'\b', word_without_negation, line[1])))
                else:    #if the word is non-negated then returns the sentence with the negated word
                    lista.append((re.sub(r'(\b' + words_found[0] + r'\b)', r'NÃO_\1', line[0]), re.sub(r'(\b' + words_found[0] + r'\b)', r'NÃO_\1', line[1])))

            #if more than one word was found then it returns all possible combinations of these words in the sentence (negated or not negated)
            else:

                list_of_words_caught = []   #this list will be used to avoid repeating the original sentence in the augmentation

                #words_found = [] #list to store what words from the list were originally in the sentence, this will needed in order to skip the case when the augmented sentence is the original sentence

                re_words = []   #this list contains the regex expression for which word of the sentence that is in the list

                #generates a regex expression just for the words found and puts the word itself and a negated version of it in "list_of_words_caught" (replacing what was in it before) for every word found
                for index, word in enumerate(set(words_found)):  #"words_found" is made into a set to eliminate repeated words
                    if word[:4] == 'NÃO_':  #in case the world is already negated then it'll add the negated word along a non-negated version of it

                        re_words.append(r'(\b' + word + '|' + word[4:] + r'\b)')    #regex expression for both the negated and non-negated word
                        list_of_words_caught.append([word]) #inserts a list with the negated word as its first element
                        list_of_words_caught[index].append(word[4:])    #adds the non-negated word as its second element in the list for that word

                    else:  #in case the world is not negated then it'll add the word along a negated version of it

                        re_words.append(r'(\b' + word + '|NÃO_' + word + r'\b)')    #regex expression for both the negated and non-negated word
                        list_of_words_caught.append([word]) #inserts a list with the original word as its first element
                        list_of_words_caught[index].append('NÃO_' + word)    #adds the negated word as its second element in the list for that word

                #makes all possible combinations of the word and their negated versions from "words_found"
                #as an example, from "EU SER ISSO AQUI" will be created the possibilities: [(SER, AQUI), (NÃO_SER, AQUI), (SER, NÃO_AQUI), (NÃO_SER, NÃO_AQUI)]
                combinations = itertools.product(*list_of_words_caught)

                #dividing the sentence into "gr" and "gi"
                sentence_gr = line[0]
                sentence_gi = line[1]

                next(combinations)  #this next is necessary in order to skip the first combination, i.e, the original sentence

                #for every possible combination it generates an augmented version of the original sentence
                for words in combinations:
                    #goes over every word of the possibility (named "words" in the loop for combinations)
                    for i, word in enumerate(words):
                        sentence_gr = re.sub(re_words[i], word, sentence_gr)    #makes the right replacement for which word in "gr"
                        sentence_gi = re.sub(re_words[i], word, sentence_gi)    #makes the right replacement for which word in "gi"

                    lista.append((sentence_gr, sentence_gi))    #inserts the augmented sentence into the list

        return lista    #returns the list, whether empty (no augmentation possible) or with the augmentations

    def __del__(self):
        if self._fd:
            self._fd.close()


# Add element to the registry
register_element(NegationAugmentation)