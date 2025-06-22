# 🧾 PDF Bill Renamer

A simple Flask web application that renames PDF bills inside a ZIP archive based on the recipient's name extracted from the content of each PDF.

## 🚀 Features

- Upload a ZIP file containing PDF bills named like `DC_XXXXXXXXXX.pdf`.
- Extracts recipient names from the PDF content.
- Renames files to `<RECIPIENT>_XXXXXXXXXX.pdf`.
- Returns a new ZIP archive for download.
- Cleans up all temporary files after download.

## 📦 Requirements

- Python 3.8+
- Flask
- PyMuPDF (`pymupdf`)
- Gunicorn

Install dependencies:

```bash
pip install -r requirements.txt
