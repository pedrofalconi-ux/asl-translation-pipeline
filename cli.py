import sys

import pipeline

# Application entry point.
if __name__ == '__main__':
    '''
    if len(sys.argv) < 2:
        print(f'Usage: python3 {sys.argv[0]} <pipeline expression>')
        quit()
    '''

    pipeline_expression = ' '.join(sys.argv[1:])
    if not pipeline_expression:
        # User didn't give a pipeline expression. Use default.
        pipeline_expression = 'translate src=./data/corpus.csv'
        print(
            f'[WARN] No pipeline specified. Defaulting to: "{pipeline_expression}"'
        )

    pl = pipeline.Pipeline()
    pl.parse_pipeline_expression(pipeline_expression)
    pl.instantiate_elements()
    pl.process()
    pl.destruct_elements()
