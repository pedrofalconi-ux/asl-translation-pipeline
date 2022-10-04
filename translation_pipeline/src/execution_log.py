import csv
import logging
import os
import sys
import time


def prepare_logging(imported_as_module=True):
    """Configure logging for the next pipeline execution."""

    # Create log dir, if it doesn't exist.
    log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "logs")
    os.makedirs(log_dir, exist_ok=True)

    # Prepare log file output.
    execution_timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    log_file_path = os.path.join(log_dir, f"pipeline {execution_timestamp}.log")
    log_file_handler = logging.FileHandler(log_file_path)
    log_file_handler.setLevel(logging.DEBUG)
    log_file_handler.setFormatter(
        logging.Formatter("[%(levelname)s] [%(asctime)s] %(message)s")
    )

    # Configure root logger output for the first time.
    logging.basicConfig(
        format="[%(levelname)s] [%(asctime)s] %(message)s",
        level=logging.INFO,
        handlers=[logging.StreamHandler(sys.stdout), log_file_handler],
    )

    # Replace old file handler.
    root_logger = logging.getLogger()
    root_logger.removeHandler(root_logger.handlers[-1])
    root_logger.addHandler(log_file_handler)

    return log_file_path, execution_timestamp


def append_to_log(log_info):
    """Append data to the global pipeline execution log."""
    execution_log_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "..", "execution_log.csv"
    )

    with open(execution_log_path, "a") as fd:
        writer = csv.writer(fd)
        writer.writerow(log_info)
