import subprocess
import threading
import time
import signal
import os
import whisper
import queue

ffmpeg_process = None
recording_started = False
recording_event = threading.Event()
result_queue = queue.Queue() # Queue to store the result

def prepare_recorder(output_file="output.wav"):
    global ffmpeg_process
    command = ["ffmpeg", "-y", "-f", "avfoundation", "-i", ":4", "-ar", "16000", "-ac", "1", "-f", "wav", output_file]
    ffmpeg_process = subprocess.Popen(command, stdin=subprocess.PIPE)

def start_recording():
    global recording_started, recording_event
    recording_started = True
    recording_event.set()

def stop_recording():
    global ffmpeg_process, recording_started, recording_event
    recording_started = False
    if ffmpeg_process:
        ffmpeg_process.stdin.write(b'\n') # Send newline to start writing the file
        ffmpeg_process.stdin.flush()
        os.kill(ffmpeg_process.pid, signal.SIGINT)
        ffmpeg_process.wait()
        ffmpeg_process = None
        threading.Thread(target=convert_wav_to_text, args=("output.wav",)).start() # Start conversion in a thread
    recording_event.clear()
    return result_queue.get()

def convert_wav_to_text(wav_file):
    try:
        model = whisper.load_model("base")
        transcribed = model.transcribe(wav_file)
        result_queue.put(transcribed) # Put result in the queue
    except Exception as e:
        print(f"Error during conversion: {e}")
        result_queue.put(None) # Put None in the queue to signal an error

def main():
    prepare_recorder("output.wav")

    time.sleep(2)

    start_recording()
    time.sleep(5)
    stop_recording()
    text = result_queue.get()
    if text:
        print(f"Converted Text: {text['text']}") # Access the actual text
    else:
        print("Conversion failed.")

    prepare_recorder("output.wav") # Reuse output file

    time.sleep(2)
    start_recording()
    time.sleep(10)
    stop_recording()
    text = result_queue.get()
    if text:
        print(f"Converted Text: {text['text']}") # Access the actual text
    else:
        print("Conversion failed.")
    print("Recording stopped.")

if __name__ == "__main__":
    main()