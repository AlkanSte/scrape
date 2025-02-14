from flask import Flask, render_template, request, jsonify
import os
from enhanced_worker_log_parser import EnhancedWorkerLogParser
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Ensure upload folder exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    
    try:
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        # Parse the log file
        parser = EnhancedWorkerLogParser()
        results = parser.parse_log(filepath)
        
        # Clean up
        os.remove(filepath)
        
        return jsonify(results)
    except Exception as e:
        app.logger.error(f"Error processing file: {str(e)}", exc_info=True)
        return jsonify({'error': f'Error processing file: {str(e)}'}), 500
    finally:
        # Ensure file is cleaned up even if there's an error
        if os.path.exists(filepath):
            os.remove(filepath)

if __name__ == '__main__':
    app.run(debug=True) 