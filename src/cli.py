import argparse
import logging
import os
import shutil
import sys
import time

import execution_log
import utils
from artifact import get_artifact_directory_by_hash

# Set up logging.
log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'logs')
os.makedirs(log_dir, exist_ok=True)
execution_timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
log_file_path = os.path.join(log_dir, f'pipeline {execution_timestamp}.log')
log_file_handler = logging.FileHandler(log_file_path)
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

def execute(pipeline_expression, execution_comment):
    '''Instantiates and executes a pipeline from the given `pipeline_expression`
    then saves execution information to the log, alongside `execution_comment`.
    '''
    pipeline_git_hash = utils.get_git_revision_hash()
    logger.info(f'Pipeline Git Revision Hash: {pipeline_git_hash}')
    logger.info(f'Execution comment: {execution_comment}')

    pl = pipeline.Pipeline()
    pl.parse_pipeline_json(pipeline_expression)
    pl.instantiate_elements()
    artifact_hash = pl.process()
    pl.destruct_elements()

    logger.info(f'Pipeline finished. Artifacts saved to: {artifact_hash}')
    execution_log.append_to_log([
        execution_timestamp,                # Timestamp
        execution_comment,                  # Description
        artifact_hash,                      # Output artifact directory
        pipeline_expression,                # Pipeline expression
        pipeline_git_hash,                  # Git hash for this repository
    ])

    # Copy logs over to artifact directory as well.
    shutil.copy(log_file_path, get_artifact_directory_by_hash(artifact_hash))

    return artifact_hash


# Application entry point.
if __name__ == '__main__':
    here = os.path.dirname(os.path.abspath(__file__))

    parser = argparse.ArgumentParser()
    parser.add_argument(
        '-p', '--pipeline', help='Path to the pipeline JSON file.',
    )
    parser.add_argument(
        '-c', '--corpus', help='Path to the corpus CSV file.', default=os.path.join(here, '..', 'data', 'corpus', 'corpus.csv')
    )
    parser.add_argument(
        '-t', '--train-hash', help='Path to the train hash, if running a test pipeline.', default=''
    )
    parser.add_argument(
        '-m', '--message', help='Execution message.', default=None
    )
    args, _ = parser.parse_known_args()

    with open(args.pipeline, 'r') as pipeline_json_file:
        pipeline_json = pipeline_json_file.read().strip()
        pipeline_expression = pipeline_json.replace('CORPUS_PATH', args.corpus).replace('TRAIN_HASH', args.train_hash)

        execution_comment = args.message
        if not execution_comment:
            execution_comment = input('Please describe this execution: ')

        execute(pipeline_expression, execution_comment)
