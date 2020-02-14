class PipelineElement():
    '''Base class for pipeline elements.'''

    # The name of this pipeline element.
    name = 'base-element'

    # If the process() function is a generator.
    is_generator = True

    def __init__(self, *args, **kwargs):
        '''Generic pipeline element constructor.'''
        pass

    def pre(self):
        pass

    def process(self, data):
        '''The actual processing step. Might be a generator returning one
        processed element of "data" per iteration, or a blocking function that
        will return after all elements of "data" have been entirely processed.
        '''
        raise NotImplementedError

    def post(self):
        pass
