import logging

import registry

logger = logging.getLogger(__name__)

class ElementStub():
    '''Contains all the necessary data to instantiate an element.'''
    name = None
    base_class = None
    params = None
    instance = None
    output = None

    def __init__(self, name, params, output):
        self.name = name
        self.base_class = registry.get_element(name)
        self.params = params
        self.output = output if isinstance(output, dict) else {'default': output}

    def process_and_pass_along(self, data=None):
        '''Calls the process() method in the element instance, takes the data
        returned and forwards it to the next element(s) to do the same.
        '''
        logger.debug(f'Processing data with element {self.name}...')
        output = self.instance.process(data)
        if isinstance(output, dict):
            # Output of the process method needs to be redirected to multiple
            # outputs.
            for key, val in output.items():
                logger.debug(f'Forwarding data to {key}...')
                self.output[key].process_and_pass_along(output[val])
        else:
            # Output can be forwarded to the default element output.
            logger.debug(f'Forwarding data to default output...')
            self.output['default'].process_and_pass_along(output)
