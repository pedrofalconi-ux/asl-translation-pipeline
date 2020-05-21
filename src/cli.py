import logging
import os
import sys
import time

import execution_log
import utils

# Set up logging.
log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'logs')
os.makedirs(log_dir, exist_ok=True)
log_file_handler = logging.FileHandler(
    os.path.join(log_dir, f'pipeline {time.strftime("%Y-%m-%d %H:%M:%S")}.log')
)
log_file_handler.setLevel(logging.INFO)
log_file_handler.setFormatter(
    logging.Formatter('[%(levelname)s] [%(asctime)s] %(message)s')
)
logger = logging.getLogger(__name__)

# Configure log output.
logging.basicConfig(
    format='[%(levelname)s] [%(asctime)s] %(message)s',
    level=logging.INFO,
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

    pipeline_git_hash = utils.get_git_revision_hash()
    logger.info(f'Git Revision Hash: {pipeline_git_hash}')
    execution_comment = input('Please describe this execution: ')

    pipeline_expression = ' '.join(sys.argv[1:])
    if not pipeline_expression:
        # User didn't give a pipeline expression. Use default.
        pipeline_expression = 'translate src=./data/corpus.csv'
        logger.warning(
            f'No pipeline specified. Defaulting to: "{pipeline_expression}"'
        )

    pl = pipeline.Pipeline()
    pl.parse_pipeline_json(pipeline_expression)
    pl.instantiate_elements()
    artifact_hash = pl.process()
    pl.destruct_elements()

    logger.info(f'Pipeline finished. Artifacts saved to: {artifact_hash}')
    execution_log.append_to_log([
        time.strftime("%Y-%m-%d %H:%M:%S"), # Timestamp
        execution_comment,                  # Description
        artifact_hash,                      # Output artifact directory
        pipeline_expression,                # Pipeline expression
        pipeline_git_hash,                  # Git hash for this repository
    ])
