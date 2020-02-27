import logging
import os
import sys
import time

import utils

# Set up logging.
os.makedirs('logs', exist_ok=True)
log_file_handler = logging.FileHandler(
    os.path.join('logs', f'pipeline {time.strftime("%Y-%m-%d %H:%M:%S")}.log')
)
log_file_handler.setLevel(logging.INFO)
log_file_handler.setFormatter(
    logging.Formatter('[%(levelname)s] [%(asctime)s] %(message)s')
)
logger = logging.getLogger(__name__)

# Configure log output.
logging.basicConfig(
    format='[%(levelname)s] [%(asctime)s] %(message)s',
    level=logging.DEBUG,
    handlers=[logging.StreamHandler(sys.stdout), log_file_handler]
)

import pipeline

# Application entry point.
if __name__ == '__main__':
    '''
    if len(sys.argv) < 2:
        print(f'Usage: python3 {sys.argv[0]} <pipeline expression>')
        quit()
    '''

    logger.info(f'Git Revision Hash: {utils.get_git_revision_hash()}')

    pipeline_expression = ' '.join(sys.argv[1:])
    if not pipeline_expression:
        # User didn't give a pipeline expression. Use default.
        pipeline_expression = 'translate src=./data/corpus.csv'
        logger.warning(
            f'No pipeline specified. Defaulting to: "{pipeline_expression}"'
        )

    pl = pipeline.Pipeline()
    pl.parse_pipeline_expression(pipeline_expression)
    pl.instantiate_elements()
    pl.process()
    pl.destruct_elements()
