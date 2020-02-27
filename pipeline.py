import logging

import registry
from elements import *

logger = logging.getLogger(__name__)

class Pipeline():
    '''Called by the CLI interface.'''

    def __init__(self):
        # Holds the pipeline elements.
        self._pipeline = []

    def parse_pipeline_expression(self, pipeline_expression):
        '''Takes a user-given `pipeline_expression`, parses it and populates
        `self._pipeline` with dictionaries containing the fields `name`,
        `class`, `parameters` and a null `instance`.
        '''
        pipeline_elements = pipeline_expression.split(' ! ')

        for element_expression in pipeline_elements:
            logger.debug(f'Processing element expression: "{element_expression}"')

            first_space = element_expression.find(' ')

            # User-friendly element name. Used to fetch from registry.
            if first_space == -1:
                element_name = element_expression
            else:
                element_name = element_expression[:first_space]

            # User-friendly element parameters list. For example:
            # ['src=Input File.txt', 'enable_masking']
            element_parameters_as_str = element_expression[first_space + 1:].split(',')

            # Dictionary version of the parameter list described above.
            element_parameters_dict = {}

            # Parse parameters string into parameter dictionary.
            for element_parameter_as_str in element_parameters_as_str:
                key_val_tuple = element_parameter_as_str.split('=')
                if len(key_val_tuple) == 2:
                    # Is a key-value tuple, assign both.
                    element_parameters_dict[key_val_tuple[0]] = key_val_tuple[1]
                elif len(key_val_tuple) == 1:
                    # Is a key-only tuple, assign True to key.
                    element_parameters_dict[key_val_tuple[0]] = True

            # Add element class and parameters to the pipeline.
            element = {
                'name': element_name,
                'class': registry.get_element(element_name),
                'parameters': element_parameters_dict,
                'instance': None,
            }

            self._pipeline.append(element)

    def instantiate_elements(self):
        '''Calls the constructor with the desired parameters for each element
        in the pipeline.
        '''
        for element in self._pipeline:
            try:
                logger.debug('Instantiating "{}"...'.format(element['name']))
                element['instance'] = element['class'](**element['parameters'])
            except Exception as ex:
                logger.error('Failed to instantiate "{}": {}'.format(element['name'], ex))
                raise ex

    def destruct_elements(self):
        '''Calls the destructor for each element in the pipeline.'''
        for element in self._pipeline:
            try:
                logger.debug('Destructing "{}"...'.format(element['name']))
                del element['instance']
            except Exception as ex:
                logger.error('Failed to destruct "{}": {}'.format(element['name'], ex))

    def process(self):
        '''Starts the pipeline processing.'''
        for element in self._pipeline:
            instance = element['instance']

            # TODO: implement this. careful here, need to handle both generators
            # and regular functions
            pass
