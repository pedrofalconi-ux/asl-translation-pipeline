import json
import logging

import element_stub
from elements import *

logger = logging.getLogger(__name__)

class Pipeline():
    '''Constructed by the CLI interface.'''

    def __init__(self):
        # Holds the pipeline elements (for calling constructors/destructors).
        self._pipeline = []

        # The element that kicks off the entire pipeline.
        self._starting_element = None

        # Elements pending connection (freshly popped off from parsed stack)
        self._elements_pending_connection = []

    def _parse_element_expression(self, element_expression):
        '''Parses an element expression string and returns a tuple containing
        the element's name and a `params` dictionary.
        '''
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

        return (element_name, element_parameters_dict)

    def _parse_element_stack(self, element_stack):
        '''Parses a list of element expression strings and dicts, returns the
        last element. In the case of a dictionary, this method will be called
        recursively with the values of each key in the dictionary.
        '''
        # The element stub that was created last. Will be used for connecting
        # the current's stub output to the previous stub's output.
        prev_element = None

        # Whether to allow pending connections to be connected to the next
        # element stub that gets created. Necessary to avoid elements being
        # connected together too early during a pipeline bifurcation.
        allow_connect_pending = False

        for popped_element in element_stack[::-1]:
            if isinstance(popped_element, dict):
                # Recursive call. Iterate through the keys and build their
                # branches.
                for output_name, inner_stack in popped_element.items():
                    self._elements_pending_connection.append({
                        'output_name': output_name,
                        'element_instance': self._parse_element_stack(inner_stack)
                    })

                # Done doing the recursive calls for all the keys, now we can
                # connect the outputs to the next element we see.
                allow_connect_pending = True
            else:
                # Regular element, add stub to the pipeline.
                name, params_dict = self._parse_element_expression(popped_element)
                element = element_stub.ElementStub(name, params_dict, prev_element)

                # If there's any pending connections (and we can connect them)
                if allow_connect_pending:
                    for element_pending_connection in self._elements_pending_connection:
                        # ...connect them to this element.
                        element.output[
                            element_pending_connection['output_name']
                        ] = element_pending_connection['element_instance']

                    # Done. Clear all pending connections.
                    self._elements_pending_connection = []
                    allow_connect_pending = False

                self._pipeline.append(element)
                prev_element = element

        return prev_element

    def parse_pipeline_json(self, pipeline_json):
        # Build the stack from the parsed JSON text.
        parsed_json = json.loads(pipeline_json)
        element_stack = [json_element for json_element in parsed_json]

        self._starting_element = self._parse_element_stack(element_stack)

    def instantiate_elements(self):
        '''Calls the constructor with the desired parameters for each element
        in the pipeline.
        '''
        logger.info('Instantiating pipeline elements...')

        for element in self._pipeline:
            try:
                logger.debug('Instantiating "{}"...'.format(element.name))
                element.instance = element.base_class(**element.params)
            except Exception as ex:
                logger.error('Failed to instantiate "{}": {}'.format(element.name, ex))
                raise ex

    def destruct_elements(self):
        '''Calls the destructor for each element in the pipeline.'''
        logger.info('Destructing pipeline...')

        for element in self._pipeline:
            try:
                logger.debug('Destructing "{}"...'.format(element.name))
                del element.instance
            except Exception as ex:
                logger.error('Failed to destruct "{}": {}'.format(element.name, ex))

    def process(self):
        '''Starts the pipeline processing.'''
        logger.info('Starting pipeline processing...')
        self._starting_element.process_and_pass_along()
