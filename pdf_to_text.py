import logging
import os
import requests
from faker import Faker
from config import config  # Import the config dictionary from config.py
import google.generativeai as genai
import pytesseract
from PIL import Image
from pdf2image import convert_from_path

# Initialize Faker to generate fake data
fake = Faker()

# Set up logging
logging.basicConfig(level=logging.INFO)

# Function to anonymize text using Faker
def anonymize_text(extracted_text):
    """
    Anonymizes extracted text by replacing real data with fake data using Faker.
    This function will look for names, email addresses, phone numbers, and addresses
    and replace them with fake data generated by Faker.
    """
    # Anonymize names (replace 'John Doe' with a fake name)
    extracted_text = extracted_text.replace("John Doe", fake.name())

    # Anonymize email addresses (replace 'johndoe@example.com' with a fake email)
    extracted_text = extracted_text.replace("johndoe@example.com", fake.email())

    # Anonymize phone numbers (replace '123-456-7890' with a fake phone number)
    extracted_text = extracted_text.replace("123-456-7890", fake.phone_number())

    # Anonymize addresses (replace '1234 Main St' with a fake address)
    extracted_text = extracted_text.replace("1234 Main St", fake.address())

    # You can add more anonymization rules based on the text structure you expect
    return extracted_text

# Function to send the extracted and anonymized text to Gemini for polishing
# Function to send the extracted and anonymized text to Gemini for polishing
def polish_with_gemini(extracted_text):
    """
    Sends anonymized text to the Gemini API for further polishing.
    """
    # Get the Gemini API key from the config dictionary
    GEMINI_API_KEY = config.get("GEMINI_API_KEY")

    if not GEMINI_API_KEY:
        logging.error("Gemini API key not configured.")
        return "Error: Gemini API key not configured."

    prompt = f"Please polish and return this text as your response. Ensure any potentially sensitive information is still anonymized: {extracted_text}"

    try:
        # Initialize the Gemini API client with the API key
        genai.configure(api_key=GEMINI_API_KEY)

        # Create the GenerativeModel instance
        model = genai.GenerativeModel(model_name="gemini-2.0-flash")

        # Request Gemini to process the text
        response = model.generate_content(
            prompt
        )

        # Check if the response has valid content and return it
        if response and hasattr(response, 'text'):
            return response.text
        elif response and hasattr(response, 'parts'):
            return "".join([part.text for part in response.parts])
        else:
            logging.warning(f"Unexpected Gemini response: {response}")
            return "Error processing with Gemini."
    except Exception as e:
        logging.error(f"Error contacting Gemini: {e}")
        return f"Error contacting Gemini: {e}"

# Function to extract text from a single PDF file
def extract_text_from_pdf(pdf_path):
    """
    Extracts text content from each page of a PDF file using OCR.

    Args:
        pdf_path (str): Path to the PDF file.

    Returns:
        str: Extracted text content from the entire PDF.
    """
    full_text = ""
    try:
        images = convert_from_path(pdf_path, dpi=300)
        for i, image in enumerate(images):
            try:
                page_text = pytesseract.image_to_string(image)
                full_text += page_text + "\n\n"
            except Exception as e:
                print(f"Error processing page {i+1} of {pdf_path}: {e}")
    except Exception as e:
        print(f"Error converting {pdf_path} to images: {e}")
    return full_text

# Function to process a single PDF: extract text, anonymize, and optionally polish
def process_pdf(pdf_path, output_dir, use_gemini=False):
    """
    Processes a single PDF file by extracting text, anonymizing it using Faker,
    and optionally polishing it using Gemini.

    Args:
        pdf_path (str): Path to the PDF file.
        output_dir (str): Path to the directory where the output text file will be saved.
        use_gemini (bool): If True, send the anonymized text to Gemini for polishing.
    """
    pdf_name = os.path.splitext(os.path.basename(pdf_path))[0]
    output_filepath = os.path.join(output_dir, f"{pdf_name}_processed.txt")

    print(f"Processing {pdf_path}...")
    extracted_text = extract_text_from_pdf(pdf_path)

    if extracted_text:
        anonymized_text = anonymize_text(extracted_text)

        final_text = anonymized_text
        if use_gemini:
            final_text = polish_with_gemini(anonymized_text)

        with open(output_filepath, "w") as outfile:
            outfile.write(final_text)
        print(f"Processed and saved to {output_filepath}")
    else:
        print(f"Could not extract text from {pdf_path}.")

def process_pdfs_in_directory(pdf_dir, output_dir, use_gemini=False):
    """
    Processes all PDF files in a directory.

    Args:
        pdf_dir (str): Path to the directory containing the PDF files.
        output_dir (str): Path to the directory where you want to save the processed text files.
        use_gemini (bool): If True, send the anonymized text to Gemini for polishing.
    """
    # 1. Create the output directory if it doesn't exist
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # 2. Iterate through all files in the directory
    for filename in os.listdir(pdf_dir):
        if filename.lower().endswith(".pdf"):
            pdf_path = os.path.join(pdf_dir, filename)
            process_pdf(pdf_path, output_dir, use_gemini)

    print("Finished processing all PDF files.")

if __name__ == "__main__":
    pdf_directory = '/Users/homeralleniii/Documents/NomiComms/Nomi_Communication_Platform/Receipts'  # Replace with your PDF directory
    output_directory = '/Users/homeralleniii/Documents/NomiComms/Nomi_Communication_Platform/Receipts/Output'  # Replace with your output directory
    use_gemini_polishing = True  # Set to True to use Gemini for polishing

    process_pdfs_in_directory(pdf_directory, output_directory, use_gemini_polishing)