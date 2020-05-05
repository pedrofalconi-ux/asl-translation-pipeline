class PipelineElement():
    '''Base class for pipeline elements.'''

    # The name of this pipeline element.
    name = 'base-element'

    # Disable caching for the output of this element.
    dont_cache_output = False

    # Element version. Useful for invalidating cache.
    version = 1

    def __init__(self, *args, **kwargs):
        '''Generic pipeline element constructor.'''
        pass

    def __del__(self):
        pass

    def process(self, data):
        '''The actual processing step. Receives the output from the previous
        element in `data` and returns the processed data for the next element.
        '''
        raise NotImplementedError
