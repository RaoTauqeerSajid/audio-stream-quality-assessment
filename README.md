
# WebSocket Audio Stream - Client & Server

This project facilitates real-time audio streaming and quality assessment over WebSocket connections. It includes a client for capturing live microphone audio or sending audio files (WAV, MP3) and a server for assessing speech quality using the SQUIM Objective model.

## My Enviornment for code testing
- Python 3.12.5
- Ubuntu 24

## Setup Instructions

### Step 1: Create and Activate a Virtual Environment

```bash
# Install virtualenv if not already installed
pip install virtualenv

# Create a virtual environment named 'env'
python3 -m venv env

# Activate the virtual environment
source env/bin/activate
```

### Step 2: Install Dependencies

Ensure you are inside the virtual environment:

```bash
# Install the required libraries from requirements.txt
pip install -r requirements.txt
```

### Step 3: Running the Server

1. Navigate to the server directory:

```bash
cd app/server
```

2. Start the WebSocket server:

```bash
python websocket_server.py
```

The server will now be listening for incoming audio streams on `ws://localhost:8000`.

### Step 4: Running the Client

1. Navigate to the client directory:

```bash
cd app/client
```

2. Start the WebSocket client:

```bash
python websocket_client.py
```

3. You will be prompted to select an audio source:
    - Press `1` to capture live microphone audio.
    - Press `2` to send an audio file (WAV or MP3).

For **live microphone streaming**, press `1`. To quit microphone streaming, press `q` and `Enter` during recording.

For **audio file transmission**, press `2` and provide the full path to a supported audio file (WAV or MP3). If an unsupported file format is provided, the system will prompt you to try again or select a different audio source.

### Step 5: Recording Microphone Audio

When you choose to stream from the microphone (`1`), the client will continuously send audio data. Press `q` to stop recording and terminate the streaming session.

### Step 6: Handling Errors

- If you attempt to send an unsupported audio file type (such as `.ogg`), you will be prompted to try again or choose another source.
- In the event of connection closure or errors, the client will automatically attempt to reconnect to the WebSocket server.

### File Structure

```
app/
├── client/
│   └── websocket_client.py  # The client-side code for sending audio data
├── server/
│   └── websocket_server.py  # The server-side code for receiving and analyzing audio data
└── requirements.txt         # Python dependencies for both client and server
```

### Key Features

- **Live audio streaming**: Capture and stream microphone audio in real-time.
- **File-based audio transmission**: Send pre-recorded audio files (WAV, MP3).
- **Speech quality analysis**: The server evaluates the audio quality based on PESQ, STOI, and SI-SDR metrics.
- **Automatic reconnection**: The client will reconnect to the server automatically if the connection is closed.

### Notes

- Ensure your microphone permissions are enabled and functional on Ubuntu 24.
- Supported file formats are WAV and MP3. Unsupported formats will trigger a retry prompt.
- The project uses Python 3.12.5, so make sure all dependencies in `requirements.txt` are installed in a Python environment compatible with your system.
