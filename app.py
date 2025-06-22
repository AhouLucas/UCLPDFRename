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
        if 'zipfile' not in request.files:
            return "No file part", 400
        file = request.files['zipfile']
        if file.filename == '':
            return "No selected file", 400

        # Save uploaded file
        filename = secure_filename(file.filename)
        input_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(input_path)

        # Generate renamed zip
        output_path = rename_and_zip(input_path)  # should return a filepath

        @after_this_request
        def cleanup(response):
            try:
                os.remove(input_path)
                os.remove(output_path)
            except Exception as e:
                app.logger.warning(f"Cleanup failed: {e}")
            return response

        return send_file(
            output_path,
            mimetype='application/zip',
            as_attachment=True,
            download_name='FacturesRenamed.zip'
        )

    return render_template("index.html")



if __name__ == "__main__":
    app.run(debug=True)