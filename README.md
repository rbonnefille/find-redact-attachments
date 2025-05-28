# Proof of Concept - Find and Redact Attachments - Zendesk

This project provides a Python script to locate and redact sensitive information in attachments. It is designed to help users process files efficiently while ensuring data privacy.

## Features

- Locate attachments in specified directories.
- Redact sensitive information from files.
- Support for multiple file formats.

## Prerequisites

- Python 3.7 or higher
- Required Python libraries (see `requirements.txt`)

## Installation

1. Navigate to the project directory:
   ```bash
   cd find-redact-attachments-python
   ```
2. Create a virtual environment (optional but recommended):

   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows use `venv\Scripts\activate`
   ```

3. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

4. Create a `.env` file in the root directory and add your environment variables. For example:

   ```env
   # .env
   SUBDOMAIN=
   EMAIL=
   API_TOKEN=
   ```

## Usage

Run the script with the following command:

```bash
python3 main.py --input <path_to_JSON_file>
```

#### Note: if you have more than one JSON file, you would need to run the script for each file separately. The script is not designed to handle multiple files at once.

### Arguments:

- `--input`: Path to the JSON file containing ticket data.

## Example

```bash
python3 main.py --input ./ticketExport.json
```

### Options

- you can edit the `main.py` file to change the `MAX_WORKERS` to more than `10` in case you want to increase the number of threads that will be used to process the attachments. **Be careful with this option, as it can lead to rate limiting from Zendesk**.

## Once the script's execution is over

- It's possible that some tickets won't be processed as their comments weren't part of the JSON export file you got from Zendesk as they were exceeding the size limit which is 1mb: [Source](<[url](https://support.zendesk.com/hc/en-us/articles/4408886165402-Exporting-ticket-user-or-organization-data-from-your-account#:~:text=A%20JSON%20file%20that%20includes%20the%20tickets%20that%20exceeded%20the%201%20MB%20limit%20and%20an%20error%20message%20letting%20you%20know%20that%20the%20reason%20the%20comments%20were%20not%20included%20was%20because%20the%20ticket%20exceeded%20the%201%20MB%20limit.%20Example%3A)>)
- In that case, you can open the generated file called `ticketToReprocess.json`, you will find an array of ticket ids that will need to be reprocessed. To reprocess those, you would need to call the [list comments endpoint](<[url](https://developer.zendesk.com/api-reference/ticketing/tickets/ticket_comments/#list-comments)>), gather all the attachment ids and redact them. **This script is not intended to do that part**.
