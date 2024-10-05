"""
@author: Tauqeer Sajid
"""

import asyncio
import websockets
import torchaudio
import torch
import numpy as np
import logging
from torchaudio.pipelines import SQUIM_OBJECTIVE

# Set up logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

# Check if CUDA is available and set device accordingly
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# Initialize the pre-trained SQUIM Objective model for assessing speech quality
objective_model = SQUIM_OBJECTIVE.get_model().to(device)

# Set thresholds for PESQ, STOI, and SI-SDR for speech quality warnings
PESQ_THRESHOLD = 1.15
STOI_THRESHOLD = 0.5
SI_SDR_THRESHOLD = 0

# Buffer to temporarily store incoming audio chunks
audio_buffer = []

# Minimum buffer size for meaningful quality assessment
MIN_BUFFER_SIZE = 16000  # 1 second of audio at 16kHz

# Variable to track the current file being processed
current_file = None
is_live_stream = False  # Track whether the input is from live microphone or a file


# Function to process and assess buffered audio data
def process_buffered_audio(is_live_stream):
    global audio_buffer

    if not audio_buffer:
        return "No audio data to process."

    # Combine the buffered chunks into a single waveform
    waveform = np.concatenate(audio_buffer, axis=0)

    # Convert the waveform to a torch tensor and move it to the appropriate device (CPU or CUDA)
    waveform = torch.from_numpy(waveform).unsqueeze(0).to(device)

    # Resample the audio to 16kHz if needed
    if waveform.shape[1] != 16000:
        waveform = torchaudio.functional.resample(
            waveform, waveform.shape[1], 16000
        ).to(device)

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
        if is_live_stream:
            return f"Warning: Speech quality is low (Live mic input)!\n{warning}"
        else:
            return f"Warning: Speech quality is low!\n{warning}"
    return "Speech quality is acceptable."


# WebSocket server handler to receive and process audio chunks
async def websocket_server(websocket, path):
    global audio_buffer, current_file, is_live_stream

    try:
        is_live_stream = False  # To track if we are receiving live (mic) or file audio

        while True:
            message = await websocket.recv()

            if isinstance(message, bytes):
                audio_chunk = np.frombuffer(message, dtype=np.float32)
                audio_buffer.append(audio_chunk)

                # For live stream (mic), process the audio periodically (every 1 second)
                if (
                    is_live_stream
                    and sum(chunk.size for chunk in audio_buffer) >= MIN_BUFFER_SIZE
                ):
                    response = process_buffered_audio(is_live_stream)
                    audio_buffer = []
                    await websocket.send(f"Live mic input\n{response}")
                elif (
                    not is_live_stream
                    and sum(chunk.size for chunk in audio_buffer) >= MIN_BUFFER_SIZE
                ):
                    response = process_buffered_audio(is_live_stream)
                    audio_buffer = []
                    await websocket.send(f"File: {current_file}\n{response}")

            elif isinstance(message, str):
                # When the client sends 'live' or 'file' as the first message
                if message.startswith("filename:"):
                    current_file = message.split("filename:")[1]
                    logging.info(f"Processing file: {current_file}")
                elif message == "live":
                    is_live_stream = True
                    audio_buffer = []
                    logging.info("Receiving live (mic) audio")
                elif message == "file":
                    is_live_stream = False
                    audio_buffer = []
                    logging.info("Receiving file audio")
                elif message == "end" and not is_live_stream:  # End signal for file
                    if audio_buffer:
                        response = process_buffered_audio(is_live_stream)
                        audio_buffer = []
                        await websocket.send(f"File: {current_file}\n{response}")
                    else:
                        await websocket.send(
                            f"File: {current_file}\nNo audio data received"
                        )

    except websockets.ConnectionClosed:
        logging.info(f"Connection closed for {current_file}")
    except Exception as e:
        logging.error(f"Error: {e}")


# Start the WebSocket server and listen on localhost:8000
async def start_server():
    logging.info("Starting WebSocket server on ws://0.0.0.0:8000...")
    ws_server = await websockets.serve(
        websocket_server,
        "0.0.0.0",
        8000,
        ping_interval=None,  # Disable ping to avoid accidental closure
    )
    await ws_server.wait_closed()


# Run the WebSocket server
if __name__ == "__main__":
    try:
        asyncio.run(start_server())
    except Exception as e:
        logging.error(f"Error: {e}")
    finally:
        logging.info("WebSocket server stopped")
