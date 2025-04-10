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

full_json_export_error = 'MaximumCommentsSizeExceeded'
redacted_file_name = 'redacted.txt'
tickets_with_attachments = []
tickets_to_reprocess = []

def request_with_rate_limit(url, headers, method, data=None):
    token_username = f"{email}/token"
    auth = (token_username, api_token)
    
    try:
        response = requests.request(method, url, json=data, auth=auth, headers=headers)
        response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)

        rate_limit = response.headers.get('X-Rate-Limit')
        rate_limit_remaining = response.headers.get('X-Rate-Limit-Remaining')
        rate_limit_reset = response.headers.get('RateLimit-Reset')

        if rate_limit:
            print(f"Rate limit: {rate_limit}")
        if rate_limit_remaining:
            print(f"Rate limit remaining: {rate_limit_remaining}")
        if rate_limit_reset:
            print(f"Rate limit reset: {rate_limit_reset}")

        return {
            "response": response,  # Or response.text if the content is not JSON
            "rate_limit": rate_limit,
            "rate_limit_remaining": rate_limit_remaining,
            "rate_limit_reset": rate_limit_reset
        }

    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 429:
            seconds_to_wait = int(e.response.headers.get('Retry-After', 60))
            print(f"Rate limited. Waiting for {seconds_to_wait} seconds...")
            time.sleep(seconds_to_wait)
            return request_with_rate_limit(url, headers, method, data)
        else:
            print(f"Request failed: {e}")
            raise

    except Exception as e:
        print(f"Request failed: {e}")
        raise



def redact_attachment(ticket_id, comment_id, attachment_id):
    url = f"https://{subdomain}.zendesk.com/api/v2/tickets/{ticket_id}/comments/{comment_id}/attachments/{attachment_id}/redact"
    headers = {'Content-Type': 'application/json'}
    try:
        result = request_with_rate_limit(url, headers, "PUT")
        response = result["response"].json()

        print(f"Redaction successful: {response['attachment']['id']} was redacted")
        print(
            f"Rate limit: {result['rate_limit']}, "
            f"Rate limit remaining: {result['rate_limit_remaining']}, "
            f"Rate limit reset: {result['rate_limit_reset']}"
        )
        return {
            "rate_limit_remaining": result["rate_limit_remaining"],
            "rate_limit_reset": result["rate_limit_reset"],
        }
    except Exception as error:
        print(f"Error redacting attachment: {error}")


def delay(ms):
    """
    Delays execution for a given number of milliseconds.
    
    Args:
        ms (int): The number of milliseconds to wait
    """
    time.sleep(ms / 1000)

def store_results_to_file(filename, results):
    """
    Stores results to a file.
    
    Args:
        filename (str): The name of the file to write to
        results (str): The content to write to the file
    """
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(results)

def format_ndjson(input_file_path, output_file_path):
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
        with open(input_file_path, 'r', encoding='utf-8') as f:
            file_content = f.read()
        
        # Split the content into lines (each line is a JSON object in NDJSON format)
        ticket_objects = [line for line in file_content.split('\n') if line.strip() != '']
        
        # Parse each line into a JSON object
        parsed_objects = [json.loads(line) for line in ticket_objects]
        
        # Write the array of JSON objects to a new file
        with open(output_file_path, 'w', encoding='utf-8') as f:
            json.dump(parsed_objects, f, indent=2)
            
        print(f"Reformatted file saved to: {output_file_path}")
    except Exception as error:
        print(f"Error processing the file: {str(error)}")

def find_attachments_to_be_redacted(tickets):
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
                        "attachmentIds": []
                    }
                    # Store all attachment IDs
                    for attachment in comment["attachments"]:
                        if redacted_file_name not in attachment["file_name"]:
                            comment_data["attachmentIds"].append(attachment["id"])

                    if len(comment_data["attachmentIds"]) > 0:
                        ticket_data["comments"].append(comment_data)
                
                elif "error" in comment and comment["error"] == full_json_export_error:
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