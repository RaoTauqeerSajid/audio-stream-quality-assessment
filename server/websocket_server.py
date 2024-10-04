"""
@author: Tauqeer Sajid
"""

import asyncio
import websockets
import torchaudio
import torch
import numpy as np
from torchaudio.pipelines import SQUIM_OBJECTIVE

# Initialize the pre-trained SQUIM Objective model for assessing speech quality
objective_model = SQUIM_OBJECTIVE.get_model()

# Set thresholds for PESQ, STOI, and SI-SDR for speech quality warnings
PESQ_THRESHOLD = 1.5
STOI_THRESHOLD = 0.6
SI_SDR_THRESHOLD = 10

# Buffer to temporarily store incoming audio chunks
audio_buffer = []

# Minimum buffer size for meaningful quality assessment (1 second of 16 kHz audio)
MIN_BUFFER_SIZE = 16000  # 1 second of audio at 16kHz

# Function to process and assess buffered audio data
def process_buffered_audio():
    global audio_buffer

    if not audio_buffer:
        return "No audio data to process."

    # Combine the buffered chunks into a single waveform
    waveform = np.concatenate(audio_buffer, axis=0)

    # Convert the waveform to a torch tensor
    waveform = torch.from_numpy(waveform).unsqueeze(0)

    # Resample the audio to 16kHz if needed
    if waveform.shape[1] != 16000:
        waveform = torchaudio.functional.resample(waveform, waveform.shape[1], 16000)

    # Assess the speech quality using the pre-trained model
    stoi_hyp, pesq_hyp, si_sdr_hyp = objective_model(waveform)

    # Generate warnings if the metrics are below the defined thresholds
    warning = ""
    if pesq_hyp[0] < PESQ_THRESHOLD:
        warning += f"PESQ below threshold: {pesq_hyp[0]}\n"
    if stoi_hyp[0] < STOI_THRESHOLD:
        warning += f"STOI below threshold: {stoi_hyp[0]}\n"
    if si_sdr_hyp[0] < SI_SDR_THRESHOLD:
        warning += f"SI-SDR below threshold: {si_sdr_hyp[0]}\n"

    # Return the warning if any metric falls below the threshold, otherwise return "acceptable"
    if warning:
        return f"Warning: Speech quality is low!\n{warning}"
    return "Speech quality is acceptable."

# Function to handle .ogg file processing more efficiently
def process_ogg_file(file_path):
    global audio_buffer

    # Load and process .ogg file in smaller chunks
    print(f"Processing .ogg file: {file_path}")
    try:
        for waveform, sample_rate in torchaudio.backend.soundfile_backend.load(file_path, frame_offset=0, num_frames=16000):
            audio_chunk = waveform.numpy()
            audio_buffer.append(audio_chunk)
        
        # Once the file is fully processed, perform the quality assessment
        if audio_buffer:
            return process_buffered_audio()
        else:
            return "No audio data found in the file."

    except Exception as e:
        print(f"Error processing .ogg file: {e}")
        return "Error processing .ogg file."

# WebSocket server handler to receive and process audio chunks
async def websocket_server(websocket, path):
    global audio_buffer
    print("WebSocket server started and ready to receive audio data...")

    try:
        is_live_stream = False  # To track if we are receiving live (mic) or file audio

        while True:
            message = await websocket.recv()

            if isinstance(message, bytes):
                print("Received audio data chunk")
                audio_chunk = np.frombuffer(message, dtype=np.float32)
                audio_buffer.append(audio_chunk)

                # For live stream (mic), process the audio periodically (every 1 second)
                if is_live_stream:
                    if sum(chunk.size for chunk in audio_buffer) >= MIN_BUFFER_SIZE:
                        response = process_buffered_audio()
                        audio_buffer = []
                        await websocket.send(response)

            elif isinstance(message, str):
                # When the client sends 'live' or 'file' as the first message
                if message == "live":
                    print("Receiving live (mic) audio")
                    is_live_stream = True
                    audio_buffer = []

                elif message == "file":
                    print("Receiving file audio")
                    is_live_stream = False
                    audio_buffer = []

                elif message == "end" and not is_live_stream:  # End signal for file
                    print("Received end of file transmission. Processing full audio file...")
                    if audio_buffer:
                        response = process_buffered_audio()
                        audio_buffer = []
                        await websocket.send(response)
                    break
            else:
                print("Received non-binary data, ignoring...")

    except websockets.ConnectionClosed:
        print("WebSocket connection closed")
    except Exception as e:
        print(f"Error: {e}")

# Start the WebSocket server and listen on localhost:8000
async def start_server():
    print("Starting WebSocket server on ws://localhost:8000...")
    ws_server = await websockets.serve(
        websocket_server, "localhost", 8000, ping_interval=None  # Disable ping to avoid accidental closure
    )
    await ws_server.wait_closed()

# Run the WebSocket server
if __name__ == "__main__":
    try:
        asyncio.run(start_server())
    except Exception as e:
        print(f"Error: {e}")
    finally:
        print("WebSocket server stopped")
