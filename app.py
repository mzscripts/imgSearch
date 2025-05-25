import os
from flask import Flask, request, jsonify, send_from_directory
import requests
from dotenv import load_dotenv
from flask_cors import CORS
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()
app = Flask(__name__, static_folder='static')
CORS(app)
SERPAPI_KEY = os.getenv("SERPAPI_KEY")

@app.route('/')
def serve_index():
    return send_from_directory(app.static_folder, 'index.html')

@app.route('/upload', methods=['POST'])
def upload_image():
    if 'image' not in request.files:
        return jsonify({'error': 'No image uploaded'}), 400

    image_file = request.files['image']
    image_path = os.path.join("temp", image_file.filename)
    image_file.save(image_path)

    # Upload image to ImgBB
    uploaded_url = upload_to_imgbb(image_path)
    if not uploaded_url:
        return jsonify({'error': 'Image upload failed'}), 500

    # Call SerpAPI reverse image search
    try:
        result_links = search_similar_images(uploaded_url)
        return jsonify({'results': result_links})
    except Exception as e:
        logger.error(f"Error during SerpAPI request: {str(e)}")
        return jsonify({'error': 'Failed to search for similar images. Please try again later.'}), 500

def upload_to_imgbb(image_path):
    imgbb_key = os.getenv("IMGBB_API_KEY")
    if not imgbb_key:
        raise ValueError("IMGBB_API_KEY is not set in the .env file.")

    with open(image_path, "rb") as f:
        response = requests.post(
            "https://api.imgbb.com/1/upload",
            data={"key": imgbb_key},
            files={"image": f}
        )
    try:
        return response.json()["data"]["url"]
    except:
        return None

def search_similar_images(image_url):
    url = "https://serpapi.com/search"
    params = {
        "engine": "google_reverse_image",
        "image_url": image_url,
        "api_key": SERPAPI_KEY
    }
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()  # Raise an exception for 4xx/5xx status codes
        results = response.json()
        return [img["link"] for img in results.get("image_results", [])[:5]]
    except requests.exceptions.RequestException as e:
        logger.error(f"SerpAPI request failed: {str(e)}")
        raise

if __name__ == '__main__':
    os.makedirs("temp", exist_ok=True)
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)))