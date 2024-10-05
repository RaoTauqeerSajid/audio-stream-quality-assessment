"""
@author: Tauqeer Sajid
"""

import websocket
import threading
import pyaudio
import torchaudio
import numpy as np
import os
import logging
import time
import sys

# Set up logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

streaming = True  # Flag to control streaming and synchronization
stop_flag = False  # Flag to signal when to stop streaming
service_running = True  # Flag to signal when the service is running
current_file = None  # Track the currently processed file

# Retry settings
RETRY_INTERVAL = 5  # seconds to wait before reconnecting


# Function to capture audio from the microphone continuously using PyAudio until stopped
def capture_audio_stream(ws, sample_rate=16000, chunk_duration=1):
    global streaming, stop_flag
    logging.info("Starting audio stream from microphone... Press 'q' to stop.")

    # Initialize PyAudio
    p = pyaudio.PyAudio()

    try:
        # Open the stream for audio capture
        stream = p.open(
            format=pyaudio.paFloat32,
            channels=1,
            rate=sample_rate,
            input=True,
            frames_per_buffer=int(chunk_duration * sample_rate),
        )

        audio_buffer = []  # To accumulate audio chunks

        while ws.sock and ws.sock.connected and streaming:
            if stop_flag:  # Check if the user wants to stop recording
                break

            # Read audio chunk
            audio_chunk = stream.read(
                int(chunk_duration * sample_rate), exception_on_overflow=False
            )
            audio_buffer.append(audio_chunk)

            # Accumulate 1 second of audio
            if len(audio_buffer) >= 1:
                # Combine the accumulated chunks into a single batch
                audio_data = b"".join(audio_buffer)

                # Send the combined batch to the server
                if ws.sock and ws.sock.connected:
                    ws.send(audio_data, opcode=websocket.ABNF.OPCODE_BINARY)

                # Clear the buffer after sending
                audio_buffer = []
            else:
                logging.info("Buffering audio...")

    except KeyboardInterrupt:
        logging.info("Audio streaming stopped by user.")
    except websocket.WebSocketConnectionClosedException:
        logging.error(
            "Attempted to send data after the WebSocket connection was closed."
        )
    except Exception as e:
        logging.error(f"Error capturing audio: {e}")
    finally:
        if "stream" in locals():
            stream.stop_stream()
            stream.close()
        p.terminate()
        logging.info("Audio streaming stopped.")


# Function to load an audio file and send it in binary chunks
def send_audio_from_file(ws, file_path, chunk_size=1024):
    global current_file
    current_file = file_path  # Track the file being processed

    # Check if the file exists before processing
    if not os.path.exists(file_path):
        logging.error(f"Error: The file {file_path} does not exist.")
        return

    logging.info(f"Sending audio from file: {file_path}")

    try:
        # Load the audio file using torchaudio
        waveform, sample_rate = torchaudio.load(file_path)

        # Convert the waveform to bytes for sending over WebSocket
        audio_data = waveform.numpy().tobytes()

        # Send the file name first
        ws.send(f"filename:{file_path}")

        # Send audio as binary in small chunks
        for i in range(0, len(audio_data), chunk_size):
            if ws.sock and ws.sock.connected:
                chunk = audio_data[i : i + chunk_size]
                ws.send(chunk, opcode=websocket.ABNF.OPCODE_BINARY)
            else:
                break

        # After sending all audio data, signal the server that transmission is complete
        if ws.sock and ws.sock.connected:
            ws.send("end")
            logging.info(f"File '{file_path}' sent. Waiting for server response...")

    except FileNotFoundError:
        logging.error(f"Error: The file {file_path} does not exist.")
    except Exception as e:
        logging.error(f"Error while sending audio: {e}")


# Function to process all audio files in a directory, including subdirectories
def send_audio_from_directory(ws, directory_path):
    # Check if the directory exists before processing
    if not os.path.isdir(directory_path):
        logging.error(f"Error: Directory {directory_path} does not exist.")
        return

    try:
        for root, dirs, files in os.walk(directory_path):
            for file_name in files:
                file_path = os.path.join(root, file_name)
                if validate_file(file_path):
                    ws.send("file")
                    send_audio_from_file(ws, file_path)
                else:
                    logging.info(f"Skipping file: {file_path} (Invalid file type)")
    except Exception as e:
        logging.error(f"Error while processing directory: {e}")


# Function to validate file type
def validate_file(file_path):
    valid_extensions = [".wav", ".mp3"]
    file_ext = os.path.splitext(file_path)[1].lower()
    return file_ext in valid_extensions


# Function to handle stopping the recording when 'q' is pressed
def listen_for_stop():
    global stop_flag
    while True:
        user_input = input()
        if user_input.strip().lower() == "q":
            stop_flag = True
            logging.info("Stopping audio streaming...")
            break


# Function to start a thread for microphone streaming
def send_audio_from_microphone(ws):
    global streaming, stop_flag

    # Reset the stop flag
    stop_flag = False

    # Use the default sample rate of the system's default input device
    p = pyaudio.PyAudio()
    default_sample_rate = p.get_default_input_device_info()["defaultSampleRate"]
    p.terminate()  # Close PyAudio after retrieving default info

    streaming = True

    # Start the microphone streaming thread
    streaming_thread = threading.Thread(
        target=capture_audio_stream, args=(ws, int(default_sample_rate))
    )
    streaming_thread.daemon = True  # Mark the thread as daemon
    streaming_thread.start()

    # Start the thread to listen for 'q' to stop recording
    stop_thread = threading.Thread(target=listen_for_stop)
    stop_thread.daemon = True  # Mark the thread as daemon
    stop_thread.start()


# Function to handle user input in a separate thread
def user_input_loop(ws):
    global service_running
    while service_running:
        # Prompt user for the input mode choice
        logging.info("Please choose input mode:")
        logging.info("1. Microphone input")
        logging.info("2. Process a single audio file")
        logging.info("3. Process all audio files in a directory")
        logging.info("4. Exit")

        choice = input("Enter the mode number (1/2/3/4): ").strip()

        if choice == "1":
            ws.send("live")  # Indicate to the server that this is live (mic) audio
            send_audio_from_microphone(ws)
        elif choice == "2":
            file_path = input("Enter the file path: ").strip()
            if validate_file(file_path) and os.path.exists(file_path):
                ws.send("file")
                send_audio_from_file(ws, file_path)
            else:
                logging.info(f"Invalid file type or file does not exist: {file_path}")
        elif choice == "3":
            directory_path = input("Enter the directory path: ").strip()
            if os.path.isdir(directory_path):
                ws.send("directory")
                send_audio_from_directory(ws, directory_path)
            else:
                logging.info(f"Directory does not exist: {directory_path}")
        elif choice == "4":
            logging.info("Exiting...")
            ws.close()
            service_running = False
            break
        else:
            logging.error("Invalid mode selected. Please choose a valid option.")


# WebSocket client setup
def on_message(ws, message):
    global current_file

    if current_file:
        logging.info(f"Server response for file '{current_file}': {message}")
    else:
        logging.info(f"Server response for: {message}")


def on_error(ws, error):
    logging.error(f"WebSocket error: {error}")


def on_close(ws, close_status_code, close_msg):
    global service_running
    logging.info(f"### WebSocket connection closed ###")
    service_running = False  # Ensure this flag is set to stop any running loops


def on_open(ws):
    # Start the user input loop in a separate thread
    input_thread = threading.Thread(target=user_input_loop, args=(ws,))
    input_thread.daemon = (
        True  # Mark the thread as daemon so it terminates with the main program
    )
    input_thread.start()


# Connect to WebSocket server with retry mechanism
def connect_to_server(ws_url):
    global service_running
    while service_running:
        try:
            ws = websocket.WebSocketApp(
                ws_url, on_message=on_message, on_error=on_error, on_close=on_close
            )
            ws.on_open = on_open
            ws.run_forever()
        except Exception as e:
            logging.error(f"Connection error: {e}")
            logging.info(f"Retrying connection in {RETRY_INTERVAL} seconds...")
            time.sleep(RETRY_INTERVAL)


# Main function to connect to the WebSocket server
if __name__ == "__main__":
    ws_url = os.getenv("WS_URL", "ws://websocket_server:8000")
    connect_to_server(ws_url)
    sys.exit(0)  # Exit the program once service_running becomes False
