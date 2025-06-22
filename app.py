import zipfile
import io
import re
import os
import sys
from pathlib import Path
from pypdf import PdfReader

from flask import Flask, render_template, request, send_file, after_this_request
from werkzeug.utils import secure_filename



app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

MAX_UPLOAD_SIZE = 50 * 1024 * 1024  # 250 MB
MAX_UNCOMPRESSED_SIZE = 200 * 1024 * 1024  # 200 MB

def is_safe_zip(zip_path):
    """Check if the zip file is safe to process."""
    total_uncompressed_size = 0
    with zipfile.ZipFile(zip_path, 'r') as zin:
        for info in zin.infolist():
            total_uncompressed_size += info.file_size
            if total_uncompressed_size > MAX_UNCOMPRESSED_SIZE:
                return False
    
    print(f"Total uncompressed size: {total_uncompressed_size} bytes")
    return True


def readrecipient(path):
    reader = PdfReader(path)
    lines = []
    for page in reader.pages:
        lines.extend(page.extract_text().split('\n'))

    return lines[15].strip()

def rename_and_zip(input_zip):
    output_zip = input_zip.split(" ")[0] + "_renamed.zip"

    with zipfile.ZipFile(input_zip, 'r') as zin:
        zin.extractall("temp")
    temp_dir = "temp"
    with zipfile.ZipFile(output_zip, 'w') as zout:
        for file_name in os.listdir(temp_dir):
            if not file_name.endswith('.pdf'):
                continue
            
            original_path = os.path.join(temp_dir, file_name)
            match = re.match(r"DC_(\d+)\.pdf", file_name)
            if not match:
                print(f"Skipping file '{file_name}': does not match expected pattern.")
                continue
            
            recipient_name = readrecipient(original_path)
            new_name = f"DC_{match.group(1)}_{recipient_name}.pdf"
            zout.write(original_path, arcname=new_name)

    # Clean up temporary directory
    for file_name in os.listdir(temp_dir):
        file_path = os.path.join(temp_dir, file_name)
        os.remove(file_path)
    os.rmdir(temp_dir)

    return output_zip


@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        try: 
            if 'zipfile' not in request.files:
                return render_template("error.html", error_message="No file part provided."), 400
            file = request.files['zipfile']
            if file.filename == '':
                return render_template("error.html", error_message="No file selected."), 400

            # Check file size
            file.seek(0, os.SEEK_END)
            file_size = file.tell()
            file.seek(0)
            if file_size > MAX_UPLOAD_SIZE:
                return render_template("error.html", error_message="File size exceeds the limit of 50 MB."), 400

            # Save uploaded file
            filename = secure_filename(file.filename)
            input_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(input_path)

            @after_this_request
            def cleanup(response):
                try:
                    os.remove(input_path)
                    os.remove(output_path)
                except Exception as e:
                    app.logger.warning(f"Cleanup failed: {e}")
                return response

            # Check for zip bomb
            if not is_safe_zip(input_path):
                os.remove(input_path)
                return render_template("error.html", error_message="The uploaded zip file is too large or contains a zip bomb."), 400

            # Generate renamed zip
            output_path = rename_and_zip(input_path)  # should return a filepath

            return send_file(
                output_path,
                mimetype='application/zip',
                as_attachment=True,
                download_name='FacturesRenamed.zip'
            )
        except Exception as e:
            # Cleanup everything in upload folder
            app.logger.error(f"Error processing file: {e}")
            for file_name in os.listdir(app.config['UPLOAD_FOLDER']):
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], file_name)
                try:
                    os.remove(file_path)
                except Exception as cleanup_error:
                    app.logger.error(f"Cleanup failed for {file_name}: {cleanup_error}")
            return render_template("error.html", error_message=str(e)), 500

    return render_template("index.html")



if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)