import argparse
import logging
import os
import shutil

import execution_log
import pipeline
import utils
from artifact import get_artifact_directory_by_hash

logger = logging.getLogger(__name__)
imported_as_module = __name__ == '__main__'

def execute(pipeline_expression, execution_comment, progress_callback_fn=None):
    '''Instantiates and executes a pipeline from the given `pipeline_expression`
    then saves execution information to the log, alongside `execution_comment`.
    '''
    log_file_path, execution_timestamp = execution_log.prepare_logging(
        imported_as_module=imported_as_module
    )

    pipeline_git_hash = utils.get_git_revision_hash()
    logger.info(f'Pipeline Git Revision Hash: {pipeline_git_hash}')
    logger.info(f'Execution comment: {execution_comment}')

    pl = pipeline.Pipeline()
    pl.parse_pipeline_json(pipeline_expression)
    pl.instantiate_elements()
    if progress_callback_fn:
        pl.set_progress_callback_fn(progress_callback_fn)

    artifact_hash = pl.process()
    pl.destruct_elements()

    logger.info(f'Pipeline finished. Artifacts saved to: {artifact_hash}')
    execution_log.append_to_log([
        execution_timestamp,                   # Timestamp
        execution_comment,                     # Description
        artifact_hash,                         # Output artifact directory
        pipeline_expression.replace('\n', ''), # Pipeline expression
        pipeline_git_hash,                     # Git hash for this repository
    ])

    # Copy logs over to artifact directory as well.
    shutil.copy(log_file_path, get_artifact_directory_by_hash(artifact_hash))

    return artifact_hash


# Application entry point.
def main():
    here = os.path.dirname(os.path.abspath(__file__))

    parser = argparse.ArgumentParser()
    parser.add_argument(
        '-p', '--pipeline', help='Path to the pipeline JSON file.',
    )
    parser.add_argument(
        '-c', '--corpus', help='Path to the corpus CSV file. Will replace any ocurrences of "CORPUS_PATH" in the pipeline JSON.',
        default=os.path.join(here, '..', 'data', 'corpus', 'corpus.csv')
    )
    parser.add_argument(
        '-t', '--train-hash', help='Train artifact hash, if running a test pipeline. Will replace any ocurrences of "TRAIN_HASH" in the pipeline JSON.',
        default=''
    )
    parser.add_argument(
        '-m', '--message', help='Execution message.', default=None
    )
    args, _ = parser.parse_known_args()

    if not args.pipeline:
        logger.error('The -p (or --pipeline) parameter is mandatory.')
        quit(1)

    with open(args.pipeline, 'r') as pipeline_json_file:
        pipeline_json = pipeline_json_file.read().strip()
        pipeline_expression = pipeline_json.replace('CORPUS_PATH', args.corpus).replace('TRAIN_HASH', args.train_hash)

        execution_comment = args.message
        if not execution_comment:
            execution_comment = input('Please describe this execution: ')

        execute(pipeline_expression, execution_comment)

if __name__ == '__main__':
    main()
