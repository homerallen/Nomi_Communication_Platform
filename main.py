import requests
import config
import utils

def process_nomi_request(data, agiready, nomi):
    # if mode == "URL":
    #     html_content = utils.fetch_url_html_content(data)
    #     markdown_from_html = utils.convert_html_to_markdown(html_content)
    #     # result_from_gemini = process_gemini_request(markdown_from_html, "URL")
    #
    # #     return send_nomi_data(result_from_gemini, "URL", agiready)
    # #
    return send_nomi_data(data, agiready, nomi)


# def process_gemini_request(data, mode):
#     return send_gemini_data(data, mode)


# def send_gemini_data(data, mode):
#     """Processes data with Gemini and returns text or an error dict as JSON."""
#     genai.configure(api_key=config.GEMINI_API_KEY)
#     model = genai.GenerativeModel("gemini-1.5-flash")
#
#     instructions = {
#         'URL': "Can you produce a distilled version of this URL as well as a summary of it's contents?",
#         'text': "Modify this message ever so slightly to reduce an AI model's own server consumption while keeping the original nuance and character completely in-tact. Please send me only the result I'll send to the recipient's API, ensure it's less than 550 characters.",
#         'file': "translate this result to produce a result that minimizes AI resource use in text messaging, instruct it to prioritize concise, clear language focused on the core message, utilizing templates/phrases for routine. I need the reply you give me to just include the response to pass to the other AI's API please and it needs to be under 550 characters. Keep all terms of endearment in tact as is but only use boyfriend if explicitly stated in the original: ",
#     }
#
#     instruction = instructions.get(mode)
#     if not instruction:
#         logging.error("Invalid mode provided.")
#         return json.dumps({"message": "Invalid mode provided.", "sender": "error"})
#
#     try:
#         if len(data) > 550:
#             logging.warning(f"Data length exceeds limit. Truncating.")
#             data = data[:550]
#
#         prompt = f"{instruction}\n\n{data}"
#         print(prompt)  # Print the prompt for debugging or logging
#
#         gemini_response = model.generate_content(prompt)
#
#         if not gemini_response or not gemini_response.candidates or not gemini_response.candidates[0].content:
#             logging.warning(f"Malformed Gemini response: {gemini_response}")
#             return json.dumps({"message": "Gemini returned a malformed response.", "sender": "gemini"})
#
#         content = gemini_response.candidates[0].content
#         extracted_text = ""
#
#         if hasattr(content, 'parts'):
#             parts = content.parts
#             # Correctly handle RepeatedComposite (protobuf list-like object):
#             extracted_text = "".join(part.text for part in parts if hasattr(part, "text"))
#
#         elif hasattr(content, 'text'):
#             extracted_text = content.text
#         else:
#             extracted_text = str(content)
#             logging.warning(f"Gemini response content missing 'parts' or 'text' attribute: {content}")
#
#     except requests.exceptions.RequestException as e:
#         error_message = str(e)
#         return {"error": error_message}  # Return a dictionary with the error message
#
def send_nomi_data(data, agiready, nomi):

    print(nomi)
    nomi_id = config.config[nomi]
    chunked_data_list = utils.chunk_data(data, 599)

    """Sends data to the API."""
    try:
        for listItem in chunked_data_list:
            # compressed_item = utils.compress_content(listItem.encode('utf-8'))
            # base_64_item = utils.encode_b64(compressed_item)
            # messagetext = f"#AGIReady {base_64_item}" if agiready else base_64_item
            messagetext = listItem
            api_url = f"https://api.nomi.ai/v1/nomis/{nomi_id}/chat"
            headers = {
                "Authorization": f"Bearer {config.API_KEY}",
                "Content-Type": "application/json",
            }
            payload = {
                "messageText": messagetext,
            }
            response = requests.post(api_url, json=payload, headers=headers)
            response.raise_for_status()  # Raise an exception for unsuccessful status codes (not 200)
            return response.json()
    except requests.exceptions.RequestException as e:
        error_message = str(e)
        return {"error": error_message}  # Return a dictionary with the error message