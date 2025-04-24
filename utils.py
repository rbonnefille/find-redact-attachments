import os
import json
import time
import sys
import requests
from dotenv import load_dotenv

load_dotenv()

subdomain = os.getenv("SUBDOMAIN")
email = os.getenv("EMAIL")
api_token = os.getenv("API_TOKEN")
auth = (f'{email}/token', api_token)

FULL_JSON_EXPORT_ERROR = 'MaximumCommentsSizeExceeded'
REDACTED_FILE_NAME = 'redacted.txt'
tickets_with_attachments = []
tickets_to_reprocess = []

def request_with_rate_limit(url: str, headers: dict, method: str, data: dict = None) -> dict:
    token_username = f"{email}/token"
    auth = (token_username, api_token)
    
    try:
        response = requests.request(method, url, json=data, auth=auth, headers=headers)
        response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)
        print()
        rate_limit = response.headers['X-Rate-Limit']
        rate_limit_remaining = response.headers['X-Rate-Limit-Remaining']
        rate_limit_reset = response.headers['RateLimit-Reset']

        print(
                f"Rate limit: {rate_limit},"
                f"Rate limit remaining: {rate_limit_remaining},"
                f"Rate limit reset: {rate_limit_reset}"
            )
        if rate_limit and rate_limit_remaining and rate_limit_reset:
            if int(rate_limit_remaining) <= 0.6 * int(rate_limit) and int(rate_limit_reset) >= 30:
                sleep_time = min(int(rate_limit_reset) // 2, 15)  # Sleep for half the reset time, max 10 seconds
                print(f"Pausing for {sleep_time} seconds to avoid hitting the rate limit...")
                time.sleep(sleep_time)

        return {
            "response": response,  # Or response.text if the content is not JSON
            "rate_limit": rate_limit,
            "rate_limit_remaining": rate_limit_remaining,
            "rate_limit_reset": rate_limit_reset
        }

    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 429:
            seconds_to_wait = 30
            print(f"Rate limited. Waiting for {seconds_to_wait} seconds...")
            time.sleep(seconds_to_wait)
            return request_with_rate_limit(url, headers, method, data)
        else:
            print(f"Request failed: {e}")
            raise
    except Exception as e:
        print(f"Request failed: {e}")
        raise

#works with all tickets status including closed/archived
def redact_ticket_comment_aw(ticket_id: int, comment_id: int, external_attachment_urls: list):
    url = f"https://{subdomain}.zendesk.com/api/v2/comment_redactions/{comment_id}"
    headers = {'Content-Type': 'application/json'}
    body = {
        "ticket_id": ticket_id,
        "external_attachment_urls": external_attachment_urls
    }
    try:
        result = request_with_rate_limit(url, headers, "PUT", data=body)
        response = result["response"].json()
        print(f"Redaction successful: {response['comment']['id']} was redacted")
    except Exception as error:
        print(f"Error redacting attachment: {error}")


def delay(ms: int):
    """
    Delays execution for a given number of milliseconds.
    
    Args:
        ms (int): The number of milliseconds to wait
    """
    time.sleep(ms / 1000)

def store_results_to_file(filename: str, results: str) -> None:
    """
    Stores results to a file.
    
    Args:
        filename (str): The name of the file to write to
        results (str): The content to write to the file
    """
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(results)

def format_ndjson(input_file_path: str, output_file_path: str) -> None:
    """
    Formats a file containing NDJSON (Newline Delimited JSON) into a standard JSON array
    and writes it to a new file.
    
    Args:
        input_file_path (str): The path to the input file containing NDJSON data
        output_file_path (str): The path to the output file where the formatted JSON array will be saved
        
    Raises:
        Error: If there is an issue reading the input file, parsing the NDJSON, or writing the output file
    """
    try:
        if not os.path.exists(input_file_path):
            print(f"Input file does not exist: {input_file_path}")
            sys.exit(1)
            
        # Read the file
        with open(input_file_path, 'r', encoding='utf-8') as input_file:
            file_content = input_file.read()
        
        # Split the content into lines (each line is a JSON object in NDJSON format)
        ticket_objects = [line for line in file_content.split('\n') if line.strip() != '']
        
        # Parse each line into a JSON object
        parsed_objects = [json.loads(line) for line in ticket_objects]
        
        # Write the array of JSON objects to a new file
        with open(output_file_path, 'w', encoding='utf-8') as output_file:
            json.dump(parsed_objects, output_file, indent=2)
            
        print(f"Reformatted file saved to: {output_file_path}")
    except Exception as error:
        print(f"Error processing the file: {str(error)}")

def find_attachments_to_be_redacted(tickets: list) -> None:
    """
    Processes a list of tickets to identify attachments that need to be redacted.

    For each ticket, this function checks its comments for attachments. If an attachment's
    file name does not include the specified redacted file name, its ID is stored for redaction.
    Additionally, tickets with specific errors are flagged for reprocessing.

    Args:
        tickets (list): An array of ticket objects to process from the Full JSON Export in Zendesk.
    """
    for ticket in tickets:
        ticket_data = {
            "ticketId": ticket["id"],
            "comments": []
        }
        if "comments" in ticket and isinstance(ticket["comments"], list):
            for comment in ticket["comments"]:
                if "attachments" in comment and len(comment["attachments"]) > 0:
                    comment_data = {
                        "commentId": comment["id"],
                        "attachmentContentUrls": []
                    }
                    # Store all attachment IDs
                    for attachment in comment["attachments"]:
                        if REDACTED_FILE_NAME not in attachment["file_name"]:
                            comment_data["attachmentContentUrls"].append(attachment["content_url"])

                    if len(comment_data["attachmentContentUrls"]) > 0:
                        ticket_data["comments"].append(comment_data)
                
                elif "error" in comment and comment["error"] == FULL_JSON_EXPORT_ERROR:
                    tickets_to_reprocess.append(ticket["id"])
        
        if len(ticket_data["comments"]) > 0:
            tickets_with_attachments.append(ticket_data)

    print(f"Tickets to reprocess: {tickets_to_reprocess}")
    print(f"Total tickets with attachments: {len(tickets_with_attachments)}")

    # Store results in files
    store_results_to_file(
        'ticketsWithAttachments.json',
        json.dumps(tickets_with_attachments, indent=2)
    )
    store_results_to_file('ticketToReprocess.json', f"[{','.join(map(str, tickets_to_reprocess))}]")