import os
import json
import sys
import argparse
import time
from utils import format_ndjson, delay, store_results_to_file, find_attachments_to_be_redacted, tickets_with_attachments, redact_attachment
from concurrent.futures import ThreadPoolExecutor, as_completed

# Set up command-line arguments
parser = argparse.ArgumentParser(description='Script to find and redact attachments in Zendesk tickets')
parser.add_argument('-i', '--input', required=True, help='path to the input file')
args = parser.parse_args()

# Get the input file path
input_file_path = args.input
output_file_path = 'reformatted-tickets.json'

# Format the NDJSON file into a standard JSON array
format_ndjson(input_file_path, output_file_path)

# Read the formatted JSON file
with open(output_file_path, 'r', encoding='utf-8') as f:
    tickets = json.load(f)

def main():
    # Find attachments that need to be redacted
    find_attachments_to_be_redacted(tickets)

    # Redact attachments
    print('Starting redaction process...')

    # Use ThreadPoolExecutor for multithreading
    with ThreadPoolExecutor(max_workers=10) as executor:  # Adjust max_workers as needed
        futures = []
        for ticket in tickets_with_attachments:
            ticket_id = ticket["ticketId"]
            for comment in ticket["comments"]:
                comment_id = comment["commentId"]
                for attachment_id in comment["attachmentIds"]:
                    futures.append(executor.submit(redact_attachment, ticket_id, comment_id, attachment_id))   
        for future in as_completed(futures):
            try:
                future.result()  # Ensure any exceptions are raised
            except Exception as e:
                print(f'Error processing attachment: {e}')
  
if __name__ == '__main__':
    main()