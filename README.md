# Find and Redact Attachments (Python)

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

## Usage

Run the script with the following command:

```bash
python3 main.py --input <path_to_directory>
```

### Arguments:

- `--input-dir`: Path to the directory containing attachments.

## Example

```bash
python3 main.py --input ./ticketExport.json
```
