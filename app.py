import logging
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import main
import voice

logging.basicConfig(level=logging.DEBUG)

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": ["http://localhost", "http://127.0.0.1:5000"]}})
app.template_folder = 'templates'

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/start_mic', methods=['GET'])  # Define a route for your method
def start_mic():
    voice.prepare_recorder()
    voice.start_recording()
    response_data = {
        "voice_text": "hello world"
    }
    return response_data


@app.route('/stop_mic', methods=['GET'])  # Define a route for your method
def stop_mic():
    transcribed = voice.stop_recording()
    response_data = {
        "voice_text": transcribed
    }
    return response_data

@app.route('/nomi_request', methods=['POST'])
def process_nomi():
    print("Processing Nomi Request")
    message = request.form.get('message')
    agiready = request.form.get('agiready')
    nomi = request.form.get('nomi')

    if not message:
        return jsonify({"error": "No message provided"}), 400

    nomi_response = main.process_nomi_request(message, agiready, nomi)

    response_data = {
        "nomi": nomi_response,
    }

    print(response_data)
    return jsonify(response_data)


if __name__ == '__main__':
    app.run(debug=True)
