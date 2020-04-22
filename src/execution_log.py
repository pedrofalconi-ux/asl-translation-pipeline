import csv

def append_to_log(log_info):
    with open('execution_log.csv', 'a') as fd:
        writer = csv.writer(fd)
        writer.writerow(log_info)
