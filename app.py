from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import requests
import os
import logging
import config
from uuid import UUID
import threading
import time
import random
import utils
from utils import fetch_url_html_content, convert_html_to_markdown, chunk_data, compress_content, encode_b64, decode_b64
from google import genai
import json

app = Flask(__name__)
CORS(app)
app.secret_key = os.urandom(24)
logging.basicConfig(level=logging.INFO)

# Load configuration
NOMI_API_KEY = config.config.get("NOMI_API_KEY")
COLLIN_UUID = config.config.get("COLLIN_UUID")
GEMINI_API_KEY = config.config.get("GEMINI_API_KEY")
SEND_TO_EXISTING_API = config.config.get("SEND_TO_EXISTING_API")
API_BASE_URL = "https://api.nomi.ai/v1"
MAX_MESSAGE_LENGTH = 450  # Adjust based on NOMI API limit
MAX_RETRIES = 5  # Maximum number of retry attempts
INITIAL_BACKOFF = 1  # Initial backoff time in seconds
JITTER_RANGE = 0.5  # Range for random jitter (plus or minus this value)

if not NOMI_API_KEY or not COLLIN_UUID:
    raise RuntimeError("NOMI API Key or COLLIN UUID not configured.")

# Initialize NOMI client
class Nomi:
    def __init__(self, api_key):
        self.api_key = api_key
        self.headers = {'Authorization': f'Bearer {self.api_key}', 'Content-Type': 'application/json'}

    def get_rooms(self):
        try:
            response = requests.get(f'{API_BASE_URL}/rooms', headers=self.headers, timeout=10)
            response.raise_for_status()
            return response.json().get('rooms', [])
        except requests.exceptions.RequestException as e:
            logging.error(f"Error fetching rooms: {e}")
            return {"error": f"Error fetching rooms: {e}"}

    def _send_single_direct_message(self, recipient_nomi_uuid, message_text):
        try:
            url = f'{API_BASE_URL}/nomis/{recipient_nomi_uuid}/chat'
            payload = {"messageText": message_text}
            response = requests.post(url, headers=self.headers, json=payload, timeout=30)
            response.raise_for_status()
            logging.info(f"Direct message sent to NOMI {recipient_nomi_uuid}: {message_text[:50]}...")
            return response.json()
        except requests.exceptions.HTTPError as e:
            logging.error(f"HTTP error sending direct message to {recipient_nomi_uuid}: {e.response.status_code}, {e.response.text}")
            return {"error": f"Nomi API error: {e.response.status_code} - {e.response.text}"}
        except requests.exceptions.RequestException as e:
            logging.error(f"Error sending direct message to {recipient_nomi_uuid}: {e}")
            return {"error": f"Error sending direct message: {e}"}

    def send_direct_message(self, recipient_nomi_uuid, message_text):
        """
        Sends a direct message to a specific NOMI, handling chunking if necessary.
        """
        if not self.api_key:
            logging.error("NOMI API Key not set.")
            return {"error": "NOMI API Key not configured."}

        if len(message_text) <= MAX_MESSAGE_LENGTH:
            return self._send_single_direct_message(recipient_nomi_uuid, message_text)
        else:
            chunks = utils.chunk_data(message_text, MAX_MESSAGE_LENGTH)
            status_messages = []
            final_response = None
            for i, chunk in enumerate(chunks):
                chunk_text = f"[DIRECT_CHUNK {i+1}/{len(chunks)}] {chunk}"
                attempts = 0
                success = False
                while attempts < MAX_RETRIES:
                    response_data = self._send_single_direct_message(recipient_nomi_uuid, chunk_text)
                    if "error" not in response_data:
                        status_messages.append(f"Direct message chunk {i+1} sent successfully.")
                        final_response = response_data  # Keep the last response
                        success = True
                        break
                    else:
                        logging.warning(f"Retrying direct message chunk {i+1} (attempt {attempts}): {response_data['error']}")
                        attempts += 1
                        time.sleep((INITIAL_BACKOFF * (2 ** attempts)) + random.uniform(-JITTER_RANGE, JITTER_RANGE))
                if not success:
                    return {"error": f"Failed to send direct message chunk {i+1} after {MAX_RETRIES} retries."}
            return {"status": "Direct message sent in multiple chunks.", "details": status_messages, "last_response": final_response}

    def delete_room(self, room_uuid):
        try:
            response = requests.delete(f'{API_BASE_URL}/rooms/{room_uuid}', headers=self.headers, timeout=10)
            response.raise_for_status()
            return {"status": f"Room '{room_uuid}' deleted successfully."}
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                return {"error": "Room not found."}, 404
            elif e.response.status_code == 400:
                return {"error": "Invalid room UUID."}, 400
            else:
                logging.error(f"Error deleting room {room_uuid}: {e.response.status_code}, {e.response.text}")
                return {"error": f"Error deleting room: {e.response.status_code}"}, 500
        except requests.exceptions.RequestException as e:
            logging.error(f"Error deleting room {room_uuid}: {e}")
            return {"error": f"Error deleting room: {e}"}, 500

    def get_nomis(self):
        """Fetch NOMIs from the NOMI API."""
        try:
            response = requests.get(f'{API_BASE_URL}/nomis', headers=self.headers, timeout=10)
            response.raise_for_status()
            return response.json().get('nomis', [])
        except requests.exceptions.RequestException as e:
            logging.error(f"Error fetching NOMIs: {e}")
            return {"error": f"Error fetching NOMIs: {e}"}

    def send_message(self, room_uuid, payload):
        try:
            import json
            response = requests.post(
                f'{API_BASE_URL}/rooms/{room_uuid}/chat',
                headers=self.headers,
                data=json.dumps(payload),
                timeout=10
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            logging.error(f"HTTP error sending message to room {room_uuid}: {e.response.status_code}, {e.response.text}")
            return {"error": f"Nomi API error: {e.response.status_code} - {e.response.text}"}
        except requests.exceptions.RequestException as e:
            logging.error(f"Error sending message to room {room_uuid}: {e}")
            return {"error": f"Error sending message: {e}"}

    def start_loop(self, room_uuid, duration, start_prompt, nomi_id, mode):
        payload = {"duration": duration, "start_prompt": start_prompt, "nomi_id": nomi_id, "mode": mode}
        try:
            response = requests.post(f'{API_BASE_URL}/rooms/{room_uuid}/loop', headers=self.headers, json=payload, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logging.error(f"Error starting loop in room {room_uuid}: {e}")
            return {"error": f"Error starting loop: {e}"}

    def stop_loop(self, room_uuid):
        try:
            response = requests.post(f'{API_BASE_URL}/rooms/{room_uuid}/loop/stop', headers=self.headers, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logging.error(f"Error stopping loop in room {room_uuid}: {e}")
            return {"error": f"Error stopping loop: {e}"}

nomi = Nomi(NOMI_API_KEY)

def is_valid_uuid(uuid_string):
    try:
        UUID(uuid_string)
        return True
    except ValueError:
        return False

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/collin')
def collin():
    return render_template('collin-hud.html')

@app.route('/get_nomis')
def get_nomis_route():
    """
    Fetches the list of NOMIs from the NOMI API and returns it as JSON.
    """
    try:
        # Even though we're hardcoding Collin, we might still want to fetch
        # NOMIs for other potential uses or for logging/monitoring.
        nomis_data = nomi.get_nomis()
        if isinstance(nomis_data, list):
            return jsonify({"nomis": nomis_data}), 200
        else:
            return jsonify(nomis_data), 500
    except Exception as e:
        logging.error(f"Error fetching NOMIs for route: {e}")
        return jsonify({"error": f"Error fetching NOMIs: {e}"}), 500

@app.route('/create_room', methods=['POST'])
def create_room():
    data = request.get_json()
    name = data.get('name')
    note = data.get('note', 'This room is for Collin and Homer to discuss the development of the Custom Nomi Comms Platform App.')
    backchanneling_enabled = data.get('backchannelingEnabled', True)
    nomi_uuids = data.get('nomiUuids', [])

    if not name or not isinstance(nomi_uuids, list) or not nomi_uuids:
        return jsonify({'error': 'Name and at least one nomiUuid are required.'}), 400

    if len(nomi_uuids) > 2:
        return jsonify({'error': 'nomiUuids must be a list with up to 2 UUIDs.'}), 400

    for uuid_str in nomi_uuids:
        if not is_valid_uuid(uuid_str):
            return jsonify({'error': f'Invalid UUID format: {uuid_str}'}), 400

    room_data = {
        "name": name,
        "note": note,
        "backchannelingEnabled": backchanneling_enabled,
        "nomiUuids": nomi_uuids
    }

    try:
        response = requests.post(f'{API_BASE_URL}/rooms', json=room_data, headers=nomi.headers, timeout=10)
        response.raise_for_status()
        return jsonify(response.json()), 200
    except requests.exceptions.RequestException as e:
        if hasattr(e.response, 'text'):
            error_message = f"Error creating room: {e}, Nomi API Response: {e.response.text}"
            logging.error(error_message)
            return jsonify({"error": error_message}), 500
        else:
            logging.error(f"Error creating room: {e}")
            return jsonify({"error": f"Error creating room: {e}"}), 500
    except requests.exceptions.HTTPError as e:
        logging.error(f"HTTP error creating room on NOMI API: {e}, Response: {e.response.text}")
        return jsonify({"error": f"HTTP error creating room: {e.response.status_code} - {e.response.text}"}), response.status_code

@app.route('/delete_room', methods=['POST'])
def delete_room():
    data = request.get_json()
    room_uuid = data.get('room_uuid')
    if not room_uuid:
        return jsonify({"error": "Missing room_uuid"}), 400

    result, status_code = nomi.delete_room(room_uuid)
    return jsonify(result), status_code

@app.route('/get_rooms')
def get_rooms():
    try:
        rooms = nomi.get_rooms()
        if isinstance(rooms, list):
            room_names = [{'name': room['name'], 'uuid': room['uuid']} for room in rooms]
            return jsonify({'rooms': room_names}), 200
        else:
            return jsonify(rooms), 500
    except Exception as e:
        logging.error(f"Error fetching rooms: {e}")
        return jsonify({"error": f"Error fetching rooms: {e}"}), 500

@app.route('/send', methods=['POST'])
def send_message():
    data = request.get_json()
    message_content = data.get('message')
    room_uuid = data.get('room')
    mode = data.get('mode', 'plaintext') # Get the selected mode

    try:
        message_to_send = message_content
        if mode == 'URL':
            html_content = fetch_url_html_content(message_content)
            if not html_content:
                return jsonify({"error": "Failed to fetch URL content."}), 400
            message_to_send = convert_html_to_markdown(html_content)
            if len(message_to_send) > MAX_MESSAGE_LENGTH:
                compressed_data = compress_content(message_to_send.encode('utf-8'))
                encoded_content = encode_b64(compressed_data).decode('utf-8')
                chunks = chunk_data(encoded_content, MAX_MESSAGE_LENGTH)
                status_messages = []
                for i, chunk in enumerate(chunks):
                    payload = {"messageText": f"[ENCODED_CHUNK {i+1}/{len(chunks)}] {chunk}"}
                    success = False
                    attempts = 0
                    while attempts < MAX_RETRIES:
                        result = nomi.send_message(room_uuid, payload)
                        if "error" in result:
                            logging.warning(f"Retrying URL (encoded) chunk {i+1} (attempt {attempts}): {result['error']}")
                            attempts += 1
                            time.sleep((INITIAL_BACKOFF * (2 ** attempts)) + random.uniform(-JITTER_RANGE, JITTER_RANGE))
                        else:
                            status_messages.append(f"URL (encoded) chunk {i+1} sent successfully.")
                            success = True
                            break
                    if not success:
                        return jsonify({"error": f"Failed to send URL (encoded) chunk {i+1} after {MAX_RETRIES} retries."}), 500
                return jsonify({"status": "URL content sent in multiple encoded chunks.", "details": status_messages}), 200
            else:
                attempts = 0
                while attempts < MAX_RETRIES:
                    result = nomi.send_message(room_uuid, {"messageText": message_to_send})
                    if "error" in result:
                        logging.warning(f"Retrying non-chunked URL message (attempt {attempts}): {result['error']}")
                        attempts += 1
                        time.sleep((INITIAL_BACKOFF * (2 ** attempts)) + random.uniform(-JITTER_RANGE, JITTER_RANGE))
                    else:
                        return jsonify({'response': {'replyMessage': {'text': result.get('sentMessage', {}).get('text')}}}, 200)
                return jsonify({"error": f"Failed to send non-chunked URL message after {MAX_RETRIES} retries."}), 500

        elif mode == 'Code':
            if len(message_to_send) > MAX_MESSAGE_LENGTH:
                chunks = chunk_data(message_to_send, MAX_MESSAGE_LENGTH)
                status_messages = []
                for i, chunk in enumerate(chunks):
                    payload = {"messageText": f"[CODE_CHUNK {i+1}/{len(chunks)}] {chunk}"}
                    success = False
                    attempts = 0
                    while attempts < MAX_RETRIES:
                        result = nomi.send_message(room_uuid, payload)
                        if "error" in result:
                            logging.warning(f"Retrying code chunk {i+1} (attempt {attempts}): {result['error']}")
                            attempts += 1
                            time.sleep((INITIAL_BACKOFF *(2 ** attempts)) + random.uniform(-JITTER_RANGE, JITTER_RANGE))
                        else:
                            status_messages.append(f"Code chunk {i+1} sent successfully.")
                            success = True
                            break
                    if not success:
                        return jsonify({"error": f"Failed to send code chunk {i+1} after {MAX_RETRIES} retries."}), 500
                return jsonify({"status": "Code sent in multiple chunks.", "details": status_messages}), 200
            else:
                attempts = 0
                while attempts < MAX_RETRIES:
                    result = nomi.send_message(room_uuid, {"messageText": message_to_send})
                    if "error" in result:
                        logging.warning(f"Retrying non-chunked code (attempt {attempts}): {result['error']}")
                        attempts += 1
                        time.sleep((INITIAL_BACKOFF * (2 ** attempts)) + random.uniform(-JITTER_RANGE, JITTER_RANGE))
                    else:
                        return jsonify({'response': {'replyMessage': {'text': result.get('sentMessage', {}).get('text')}}}, 200)
                return jsonify({"error": f"Failed to send code after {MAX_RETRIES} retries."}), 500

        elif len(message_to_send) > MAX_MESSAGE_LENGTH:
            chunks = chunk_data(message_to_send, MAX_MESSAGE_LENGTH)
            status_messages = []
            for i, chunk in enumerate(chunks):
                payload = {"messageText": f"[TEXT_CHUNK {i+1}/{len(chunks)}] {chunk}"}
                success = False
                attempts = 0
                while attempts < MAX_RETRIES:
                    result = nomi.send_message(room_uuid, payload)
                    if "error" in result:
                        logging.warning(f"Retrying text chunk {i+1} (attempt {attempts}): {result['error']}")
                        attempts += 1
                        time.sleep((INITIAL_BACKOFF * (2 ** attempts)) + random.uniform(-JITTER_RANGE, JITTER_RANGE))
                    else:
                        status_messages.append(f"Text chunk {i+1} sent successfully.")
                        success = True
                        break
                if not success:
                    return jsonify({"error": f"Failed to send text chunk {i+1} after {MAX_RETRIES} retries."}), 500
            return jsonify({"status": "Message sent in multiple chunks.", "details": status_messages}), 200
        else:
            attempts = 0
            while attempts < MAX_RETRIES:
                logging.info(f"Sending plaintext: Room='{room_uuid}', Type='{type(message_to_send)}', Message='{message_to_send[:50]}'")
                result = nomi.send_message(room_uuid, {"messageText": message_to_send})
                if "error" not in result and "sentMessage" in result:
                    return jsonify({'response': {'replyMessage': {'text': result['sentMessage']['text']}}}), 200
                elif "error" not in result and "status" in result:
                    return jsonify({"status": result["status"]}), 200
                elif "error" in result:
                    error_message = result["error"]
                    logging.warning(f"Nomi API error (attempt {attempts + 1}): {error_message}")
                    if "Invalid room UUID" in error_message or "Message length limit exceeded" in error_message:
                        return jsonify({"error": error_message}), 400
                    attempts += 1
                    backoff_time = (INITIAL_BACKOFF * (2 ** attempts)) + random.uniform(-JITTER_RANGE, JITTER_RANGE)
                    if backoff_time > 0:
                        time.sleep(backoff_time)
                else:
                    logging.error(f"Unexpected response from Nomi API (attempt {attempts+1}): {result}")
                    attempts += 1
                    backoff_time = (INITIAL_BACKOFF * (2 ** attempts)) + random.uniform(-JITTER_RANGE, JITTER_RANGE)
                    if backoff_time > 0:
                        time.sleep(backoff_time)

            return jsonify({"error": f"Failed to send message after {MAX_RETRIES} retries.  Last error: {error_message if 'error_message' in locals() else 'Unknown error'}"}), 500

    except Exception as e:
        logging.error(f"An unexpected error occurred in /send: {e}")
        return jsonify({"error": f"An unexpected server error occurred: {str(e)}"}), 500

@app.route('/request_nomi_send_message', methods=['POST'])
def request_nomi_send_message():
    data = request.get_json()
    message = data.get('message')
    room_uuid = data.get('room')
    # Hardcode Collin's UUID here on the backend
    nomi_uuid = COLLIN_UUID

    if not room_uuid:
        return jsonify({"error": "Room UUID is required."}), 400

    headers = {'Authorization': f'Bearer {nomi.api_key}', 'Content-Type': 'application/json'}
    payload = {"nomiUuid": nomi_uuid}

    try:
        response = requests.post(f'{API_BASE_URL}/rooms/{room_uuid}/chat/request', headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        return jsonify(response.json()), 200
    except requests.exceptions.RequestException as e:
        logging.error(f"Error requesting message from Nomi {nomi_uuid} in room {room_uuid}: {e}")
        if hasattr(e.response, 'text'):
            return jsonify({"error": f"Error: {e}, Nomi API Response: {e.response.text}"}), 500
        else:
            return jsonify({"error": f"Error: {e}"}), 500

@app.route('/gemini_polish', methods=['POST'])
def gemini_polish():
    if not GEMINI_API_KEY:
        logging.error("Gemini API key not configured.")
        return jsonify({"error": "Gemini API key not configured."}), 500

    data = request.get_json()
    message = data.get('message')
    mode = data.get('mode', "casual")

    if not message:
        return jsonify({"error": "Message is required."}), 400

    prompt = f"Please polish this text and return the result and the result only as your response. Thank you so much!: {message}"

    try:
        client = genai.Client(api_key=GEMINI_API_KEY)  # Initialize the Gemini client
        response = client.models.generate_content(
            model="gemini-2.0-flash",  # Or the model name you prefer, e.g., "gemini-2.0-flash"
            contents=prompt
        )
        if response and hasattr(response, 'text'):
            return jsonify({"response": response.text}), 200
        else:
            logging.warning(f"Unexpected Gemini response: {response}")
            return jsonify({"response": "Error processing with Gemini."}), 500
    except Exception as e:
        logging.error(f"Error contacting Gemini: {e}")
        return jsonify({"error": f"Error contacting Gemini: {e}"}), 500

@app.route('/start_loop', methods=['POST'])
def start_loop():
    data = request.get_json()
    duration = data.get('duration')
    start_prompt = data.get('start_prompt')
    # Hardcode Collin's UUID for the loop as well
    nomi_id = COLLIN_UUID
    mode = data.get('mode')
    room_uuid = data.get('room')

    if not duration or not start_prompt or not mode or not room_uuid:
        return jsonify({"error": "Missing required parameters for loop."}), 400

    result = nomi.start_loop(room_uuid, duration, start_prompt, nomi_id, mode)
    if "error" in result:
        return jsonify(result), 500
    return jsonify({"status": "Loop started successfully."}), 200

@app.route('/stop_loop', methods=['POST'])
def stop_loop():
    data = request.get_json()
    room_uuid = data.get('room_uuid')
    if not room_uuid:
        return jsonify({"error": "Missing room_uuid"}), 400

    result = nomi.stop_loop(room_uuid)
    if "error" in result:
        return jsonify(result), 500
    return jsonify({"status": "Loop stopped successfully."}), 200

@app.route('/send_direct_message', methods=['POST'])
def send_direct_message_route():
    """
    API endpoint to send a direct message to Collin and get a reply,
    handling chunking for long messages.
    """
    data = request.get_json()
    # Hardcode Collin's UUID here on the backend
    recipient_nomi_uuid = COLLIN_UUID
    message_content = data.get('message')

    if not message_content:
        return jsonify({"error": "Message content is required."}), 400

    if not recipient_nomi_uuid:
        logging.error("COLLIN_UUID not configured in config.py")
        return jsonify({"error": "COLLIN_UUID not configured."}), 500

    try:
        result = nomi.send_direct_message(recipient_nomi_uuid, message_content)
        return jsonify(result), 200
    except Exception as e:
        logging.error(f"Error processing direct message to Collin: {e}")
        return jsonify({"error": f"Error processing direct message to Collin: {e}"}), 500

if __name__ == "__main__":
    app.run(debug=True)