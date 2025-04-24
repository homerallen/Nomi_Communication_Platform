import json
import base64
import zlib
import requests
from markdownify import markdownify as md


def chunk_data(data, max_chunk_size=450):
    """
  Chunks the provided data into smaller pieces of a specified maximum size.

  Args:
      data: The data to be chunked (usually a string).
      max_chunk_size: The maximum size of each chunk (default: 850 characters).

  Returns:
      A list of data chunks.
  """

    chunks = []
    current_chunk = ""
    for char in data:
        current_chunk += char
        if len(current_chunk) >= max_chunk_size:
            chunks.append(current_chunk)
            current_chunk = ""
    if current_chunk:
        chunks.append(current_chunk)

    return chunks


def escape_content(content):
    escaped_content = json.dumps(content)  # Escape for JSON
    return escaped_content

def compress_content(content):
    # You CANNOT directly embed the compressed data (bytes) in JSON:
    # json_data = {"compressed": compressed_data}  # This will raise a TypeError
    compressed_content = zlib.compress(content)
    return compressed_content

def decompress_content(content):
    decompressed_content = zlib.decompress(content)
    return decompressed_content

def encode_b64(content):
    #encodes compressed content into a TEXT representation
    return base64.b64encode(content)

def decode_b64(content):
    return base64.b64decode(content)

def fetch_url_html_content(url):
    try:
        response = requests.get(url)
        response.raise_for_status()  # Raise an exception for bad status codes (4xx or 5xx)
        html_content = response.text
        return html_content
    except requests.exceptions.RequestException as e:
        print(f"Error fetching URL: {e}")
        return None

def convert_html_to_markdown(html):
    markdown_content = md(html)
    return markdown_content

# def pdf_to_images(pdf_path, output_folder="output_images", zoom_x=2.0, zoom_y=2.0, rotation_angle=0):
#     """
#     Converts a PDF to a series of PNG images.
#
#     Args:
#         pdf_path (str): Path to the PDF file.
#         output_folder (str, optional): Folder to save the images. Defaults to "output_images".
#         zoom_x (float, optional): Horizontal zoom factor. Defaults to 2.0.
#         zoom_y (float, optional): Vertical zoom factor. Defaults to 2.0.
#         rotation_angle (int, optional): Rotation angle in degrees. Defaults to 0.
#     """
#     try:
#         if not os.path.exists(output_folder):
#             os.makedirs(output_folder)
#
#         doc = fitz.open(pdf_path)
#         mat = fitz.Matrix(zoom_x, zoom_y).preRotate(rotation_angle)
#         for page_num in range(doc.page_count):
#             page = doc[page_num]
#             pix = page.get_pixmap(matrix=mat) # added matrix to control zoom and rotation
#             output_path = os.path.join(output_folder, f"page_{page_num + 1}.png")
#             pix.save(output_path)
#         print(f"PDF converted to images in {output_folder}")
#     except fitz.fitz.FileNotFoundError:
#         print(f"Error: PDF file not found at {pdf_path}")
#     except fitz.fitz.FileDataError:
#         print(f"Error: Invalid PDF file: {pdf_path}")
#     except Exception as e:
#         print(f"An error occurred: {e}")
#
# def write_string_to_file(outputfile, output):
#     """Writes a string to a file specified by the user."""
#
#     try:
#         filename = outputfile
#         output_string = output
#
#         with open(filename, 'w') as outfile:  # 'w' for write mode (overwrites)
#             outfile.write(output_string + '\n')  # Add a newline character
#
#         print(f"String written to {filename} successfully.")
#
#     except Exception as e:  # Catch potential errors (e.g., file not found, permissions)
#         print(f"An error occurred: {e}")