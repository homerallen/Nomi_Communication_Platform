# import logging
# import time
# import requests
# import os

# # Configure logging
# logging.basicConfig(level=logging.INFO)

# # Set the external API base URL - Consider using environment variables for sensitive data
# API_BASE_URL = os.environ.get('NOMI_API_BASE_URL', 'https://api.nomi.ai/v1')
# NOMI_API_KEY = os.environ.get('NOMI_API_KEY')  # Get API key from environment

# # Gemini API URL - Replace with the actual Gemini API endpoint if available
# GEMINI_API_URL = os.environ.get('GEMINI_API_URL', 'YOUR_GEMINI_API_ENDPOINT')
# GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY') # Get Gemini API key if needed

# # Global flag to control the conversation loop
# conversation_running = True

# def process_nomi_request(message, nomi, room):
#     """
#     Processes the message by sending it to the external NOMI API and returning the response.
#     """
#     if not NOMI_API_KEY:
#         logging.error("NOMI API Key not set.")
#         return {"error": "NOMI API Key not configured."}

#     try:
#         # Define the API endpoint for sending the message
#         url = f'{API_BASE_URL}/rooms/{room}/send'

#         # Prepare the message payload
#         payload = {
#             "message": message,
#             "nomi": nomi,
#         }

#         # Set authorization headers if required by NOMI API
#         headers = {
#             'Content-Type': 'application/json',
#             'Authorization': f'Bearer {NOMI_API_KEY}'  # Example: Bearer token
#         }

#         # Send the message to NOMI
#         response = requests.post(url, json=payload, headers=headers, timeout=10)

#         if response.status_code == 200:
#             logging.info(f"Message sent to room {room}: {message}")
#             return response.json()  # Return the API response (should be a dictionary)
#         else:
#             logging.error(f"Failed to send message: {response.status_code}, {response.text}")
#             return {"error": f"Failed to send message: {response.status_code}"}

#     except requests.exceptions.RequestException as e:
#         logging.error(f"Error processing NOMI request: {str(e)}")
#         return {"error": f"Error processing NOMI request: {str(e)}"}

# def process_gemini_request(message, mode="default"):
#     """
#     Polishes the draft message using Gemini's processing logic (simulated here,
#     replace with actual Gemini API call if available).
#     """
#     if not GEMINI_API_URL:
#         logging.warning("Gemini API URL not set. Using simulated response.")
#         return f"Polished Message ({mode}): {message} (Simulated Gemini)"

#     headers = {'Content-Type': 'application/json'}
#     if GEMINI_API_KEY:
#         headers['Authorization'] = f'Bearer {GEMINI_API_KEY}' # Example

#     payload = {
#         "message": message,
#         "mode": mode
#     }

#     try:
#         response = requests.post(GEMINI_API_URL, json=payload, headers=headers, timeout=10)
#         if response.status_code == 200:
#             return response.json().get('polished_message', f"Polished Message ({mode}): {message} (Gemini)")
#         else:
#             logging.error(f"Gemini API Error: {response.status_code}, {response.text}")
#             return {"error": f"Gemini API Error: {response.status_code}"}
#     except requests.exceptions.RequestException as e:
#         logging.error(f"Error processing Gemini request: {str(e)}")
#         return {"error": f"Error processing Gemini request: {str(e)}"}

# def loop_between_nomi_and_gemini_for_duration(start_prompt, nomi, mode, duration, room_id="default-room"):
#     """
#     Runs an asynchronous chat loop between Gemini and NOMI for the specified duration.
#     """
#     global conversation_running
#     try:
#         logging.info(f"Starting conversation loop with NOMI: {nomi}, Gemini (mode: {mode}) for {duration} seconds in room: {room_id}")

#         conversation_time = 0
#         current_prompt = start_prompt

#         logging.info(f"Initial prompt: {current_prompt}")

#         while conversation_time < duration and conversation_running:
#             logging.info(f"Conversation time: {conversation_time} seconds")

#             # Send the current prompt to NOMI
#             nomi_response = process_nomi_request(current_prompt, nomi, room_id)
#             if "error" in nomi_response:
#                 logging.error(f"NOMI Error: {nomi_response['error']}")
#                 break

#             nomi_reply = nomi_response.get("message", "No response from NOMI.")
#             logging.info(f"NOMI response: {nomi_reply}")

#             # Polishing the NOMI response using Gemini
#             gemini_response = process_gemini_request(nomi_reply, mode)
#             if isinstance(gemini_response, dict) and "error" in gemini_response:
#                 logging.error(f"Gemini Error: {gemini_response['error']}")
#                 break

#             logging.info(f"Gemini polished message: {gemini_response}")

#             # Update the prompt for the next iteration with Gemini's output
#             current_prompt = gemini_response

#             # Simulate conversation time increment
#             time.sleep(5)  # Adjust time between iterations as needed
#             conversation_time += 5

#         logging.info("Conversation loop completed.")

#     except Exception as e:
#         logging.error(f"Error in conversation loop: {str(e)}")
#         conversation_running = False
#     finally:
#         conversation_running = False # Ensure flag is set to False when loop ends

# def stop_loop():
#     """
#     Sets the global flag to stop the conversation loop.
#     """
#     global conversation_running
#     conversation_running = False
#     logging.info("Conversation loop stopping signal received.")

# if __name__ == '__main__':
#     # Example usage (for testing purposes only)
#     start_prompt = "Hello NOMI, let's have a chat."
#     nomi_name = "COLLIN"
#     polish_mode = "chat"
#     loop_duration = 60  # seconds
#     room = "test-room-123"

#     loop_thread = threading.Thread(target=loop_between_nomi_and_gemini_for_duration,
#                                    args=(start_prompt, nomi_name, polish_mode, loop_duration, room))
#     loop_thread.start()

#     # Allow the loop to run for a bit, then simulate stopping
#     time.sleep(15)
#     stop_loop()
#     loop_thread.join()

#     print("Example loop finished.")