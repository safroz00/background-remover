"""
Background Removal API - Flask Backend
Install dependencies: pip install flask rembg pillow flask-cors gunicorn requests
Run locally:     python app.py
Run production:  gunicorn app:app
"""

from flask import Flask, request, send_file, jsonify
from flask_cors import CORS
from rembg import remove
from PIL import Image
import io
import os
import threading
import time

app = Flask(__name__)
CORS(app)

# Configuration
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp'}

# -------------------------------------------------------
# Keep-alive ping (prevents Render free tier from sleeping)
# Set RENDER_URL environment variable in Render dashboard
# Example: https://your-app-name.onrender.com
# -------------------------------------------------------
RENDER_URL = os.environ.get('RENDER_URL', '')

def keep_alive():
    while True:
        time.sleep(14 * 60)  # ping every 14 minutes
        if RENDER_URL:
            try:
                import requests as req
                req.get(f"{RENDER_URL}/health", timeout=10)
                print("Keep-alive ping sent successfully.")
            except Exception as e:
                print(f"Keep-alive ping failed: {e}")

if RENDER_URL:
    t = threading.Thread(target=keep_alive, daemon=True)
    t.start()
    print(f"Keep-alive started for: {RENDER_URL}")

# -------------------------------------------------------

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    return jsonify({
        'service': 'Background Removal API',
        'status': 'running',
        'endpoints': {
            'remove_background': 'POST /remove-background',
            'health': 'GET /health'
        }
    })

@app.route('/remove-background', methods=['POST'])
def remove_background():
    try:
        if 'image' not in request.files:
            return jsonify({'error': 'No image file provided'}), 400

        file = request.files['image']

        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400

        if not allowed_file(file.filename):
            return jsonify({'error': 'Invalid file type. Use PNG, JPG, JPEG, or WebP'}), 400

        # Read and check file size
        file_data = file.read()
        if len(file_data) > MAX_FILE_SIZE:
            return jsonify({'error': 'File too large. Max size is 10MB'}), 400

        # Open and process image
        input_image = Image.open(io.BytesIO(file_data))
        output_image = remove(input_image)

        # Save to bytes and return
        img_io = io.BytesIO()
        output_image.save(img_io, 'PNG')
        img_io.seek(0)

        return send_file(
            img_io,
            mimetype='image/png',
            as_attachment=True,
            download_name='background-removed.png'
        )

    except Exception as e:
        print(f"Error processing image: {str(e)}")
        return jsonify({'error': f'Processing failed: {str(e)}'}), 500


@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'healthy', 'message': 'API is running'}), 200


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
