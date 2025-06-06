import json
import argparse
import timeit
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from utils import (
    format_ndjson, find_attachments_to_be_redacted, 
    tickets_with_attachments, redact_ticket_comment_aw, merge_ndjson_files
)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Set up command-line arguments
parser = argparse.ArgumentParser(
    description='Script to find and redact attachments in Zendesk tickets'
)
parser.add_argument(
    '-i', '--input', required=True, 
    help='path to the folder containing the NDJSON files from the Zendesk export'
)

args = parser.parse_args()

# Get the input file path
INPUT_FOLDER_PATH = args.input
# Set the maximum number of workers for multithreading
MAX_WORKERS = 10
# Set output file path
OUTPUT_FILE_NAME = 'reformatted-tickets.json'

def main():
    """
    Main function to find and redact attachments in Zendesk tickets.
    """
    # Merge ndjson files from the input directory
    merged_ndjson_file = merge_ndjson_files(INPUT_FOLDER_PATH)
    # Format the NDJSON file into a standard JSON array
    format_ndjson(input_file=merged_ndjson_file, output_file=OUTPUT_FILE_NAME)
   # Read the formatted JSON file
    with open(OUTPUT_FILE_NAME, 'r', encoding='utf-8') as f:
        tickets = json.load(f)
    #Find attachments that need to be redacted
    find_attachments_to_be_redacted(tickets=tickets)

    # Redact attachments
    logging.info('Starting redaction process...')

    # Count the total number of attachments to be processed
    total_attachments = sum(
        len(comment["attachmentContentUrls"]) 
        for ticket in tickets_with_attachments 
        for comment in ticket["comments"]
    )
    processed_attachments = 0

    # Use ThreadPoolExecutor for multithreading
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = []
        for ticket in tickets_with_attachments:
            ticket_id = ticket["ticketId"]
            for comment in ticket["comments"]:
                comment_id = comment["commentId"]
                for attachment_url in comment["attachmentContentUrls"]:
                    futures.append(executor.submit(redact_ticket_comment_aw, ticket_id=ticket_id, comment_id=comment_id, external_attachment_urls=[attachment_url],))
        
        for future in as_completed(futures):
            try:
                future.result()  # Ensure any exceptions are raised
                processed_attachments += 1
                remaining_attachments = total_attachments - processed_attachments
                logging.info(f'Remaining attachments to process: {remaining_attachments}/{total_attachments}')
            except Exception as e:
                logging.error(f'Error processing attachment: {e}')
  
if __name__ == '__main__':
    start_time = timeit.default_timer()
    main()
    elapsed_time = timeit.default_timer() - start_time
    logging.info(f'Total execution time: {elapsed_time:.2f} seconds, redacted {len(tickets_with_attachments)} tickets')