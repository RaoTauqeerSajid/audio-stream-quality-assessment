"""
@author: Tauqeer Sajid
"""

import websocket
import sys
import threading
import select
import pyaudio
import torchaudio
import numpy as np
import os

# Flag to control streaming
streaming = True

# Function to capture audio from the microphone continuously using PyAudio until stopped
def capture_audio_stream(ws, sample_rate=16000, chunk_duration=1):
    global streaming
    print("Starting audio stream from microphone... Press 'q' to stop.")
    
    # Initialize PyAudio
    p = pyaudio.PyAudio()
    
    # Open the stream for audio capture
    stream = p.open(format=pyaudio.paFloat32,
                    channels=1,
                    rate=sample_rate,
                    input=True,
                    frames_per_buffer=int(chunk_duration * sample_rate))

    audio_buffer = []  # To accumulate audio chunks

    try:
        while ws.sock and ws.sock.connected and streaming:
            # Read audio chunk
            audio_chunk = stream.read(int(chunk_duration * sample_rate))
            audio_buffer.append(audio_chunk)

            # Accumulate 1 second of audio
            if len(audio_buffer) >= 1:
                # Combine the accumulated chunks into a single batch
                audio_data = b''.join(audio_buffer)

                # Send the combined batch to the server
                if ws.sock and ws.sock.connected:
                    ws.send(audio_data, opcode=websocket.ABNF.OPCODE_BINARY)

                # Clear the buffer after sending
                audio_buffer = []
            else:
                print("Buffering audio...")
    except KeyboardInterrupt:
        print("Audio streaming stopped by user.")
    except websocket.WebSocketConnectionClosedException:
        print("Attempted to send data after the WebSocket connection was closed.")
    finally:
        stream.stop_stream()
        stream.close()
        p.terminate()

# Function to load an audio file and send it in binary chunks
def send_audio_from_file(ws, file_path, chunk_size=1024):
    print(f"Sending audio from file: {file_path}")

    try:
        # Load the audio file using torchaudio
        waveform, sample_rate = torchaudio.load(file_path)

        # Convert the waveform to bytes for sending over WebSocket
        audio_data = waveform.numpy().tobytes()

        # Send audio as binary in small chunks
        for i in range(0, len(audio_data), chunk_size):
            if ws.sock and ws.sock.connected:
                chunk = audio_data[i:i + chunk_size]
                ws.send(chunk, opcode=websocket.ABNF.OPCODE_BINARY)
            else:
                print("WebSocket connection is closed, stopping transmission.")
                break

        # After sending all audio data, signal the server that transmission is complete
        if ws.sock and ws.sock.connected:
            ws.send("end")
            print("Sent 'end' signal to the server.")
        
    except FileNotFoundError:
        print(f"Error: The file {file_path} does not exist.")
    except Exception as e:
        print(f"Error while sending audio: {e}")

# Function to validate file type
def validate_file(file_path):
    # Check if the file extension is either .wav or .mp3
    valid_extensions = ['.wav', '.mp3']
    file_ext = os.path.splitext(file_path)[1].lower()
    return file_ext in valid_extensions

# Function to listen for user input to stop the streaming
def listen_for_stop_signal(ws):
    global streaming
    print("Press 'q' to stop the streaming...")
    while streaming:
        if sys.stdin in select.select([sys.stdin], [], [], 0)[0]:
            user_input = input().strip().lower()
            if user_input == 'q':
                streaming = False
                ws.close()
                print("WebSocket connection closed by user.")
                break

# Function to start a thread for microphone streaming and user input listener
def send_audio_from_microphone(ws, sample_rate=16000, chunk_duration=1):
    global streaming
    streaming = True

    # Start the audio streaming thread
    streaming_thread = threading.Thread(target=capture_audio_stream, args=(ws, sample_rate, chunk_duration))
    streaming_thread.start()

    # Start the listener for stop signal
    input_listener_thread = threading.Thread(target=listen_for_stop_signal, args=(ws,))
    input_listener_thread.start()

# WebSocket client setup
def on_message(ws, message):
    print(f"Server response: {message}")

def on_error(ws, error):
    print(f"WebSocket error: {error}")

def on_close(ws, close_status_code, close_msg):
    print(f"### WebSocket connection closed ###")
    print(f"Close status code: {close_status_code}, Close message: {close_msg}")
    
    # Reconnect after the connection is closed
    print("Reconnecting to the WebSocket server...")
    connect_to_server(ws_url)

def on_open(ws):
    while True:
        choice = input("Select audio source (1 for microphone, 2 for file): ")

        if choice == "1":
            ws.send("live")  # Indicate to the server that this is live (mic) audio
            print("Starting to capture audio from the microphone.")
            send_audio_from_microphone(ws)
            break
        elif choice == "2":
            ws.send("file")  # Indicate to the server that this is a file transmission
            file_path = input("Enter the path to your audio file (e.g., 'path_to_your_audio_file.wav'): ")
            if validate_file(file_path):
                send_audio_from_file(ws, file_path)
                break
            else:
                print("Invalid file type. Only .wav and .mp3 files are supported. Please try again.")
        else:
            print("Invalid choice. Please try again.")

# Connect to WebSocket server
def connect_to_server(ws_url):
    print(f"Attempting to connect to {ws_url}...")
    ws = websocket.WebSocketApp(ws_url, on_message=on_message, on_error=on_error, on_close=on_close)
    ws.on_open = on_open
    ws.run_forever()

# Connect to WebSocket server
if __name__ == "__main__":
    ws_url = "ws://localhost:8000"
    connect_to_server(ws_url)
