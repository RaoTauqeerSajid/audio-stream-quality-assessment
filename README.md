
# WebSocket Audio Stream - Client & Server

This project is all about enabling real-time audio streaming and speech quality assessment over WebSocket connections. The setup includes a client for capturing live microphone audio or sending audio files (WAV, MP3), and a server that analyzes the speech quality using the **SQUIM Objective model**. To boost performance, the server taps into GPU resources via the NVIDIA Container Toolkit.

## Environment for Testing
Here's what you'll need to get everything running:
- **Python 3.12.5**
- **Ubuntu 24**
- **CUDA 12.2** (GPU support via Docker)

## Setup Instructions

### Step 1: Set Up NVIDIA Container Toolkit

To ensure the server uses GPU, you need to install the **NVIDIA drivers** and **NVIDIA Container Toolkit**.

1. **Install the Toolkit** by running the following:

   ```bash
   curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg      && curl -s -L https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list |        sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' |        sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list

   sudo apt-get update

   sudo apt-get install -y nvidia-container-toolkit
   ```

2. After that, restart Docker to apply the changes:
   ```bash
   sudo systemctl restart docker
   ```

### Step 2: Build and Run with Docker Compose

Now, clone the repository, navigate to the project folder, and run Docker Compose to build the client and server:

```bash
docker-compose up -d --build
```

This command will spin up both the `websocket_server` (which uses the GPU) and the `websocket_client`.

### Step 3: Running the WebSocket Client

The WebSocket client can send either live audio or pre-recorded audio files to the server. Here’s how to get started:

1. Launch the client:
   ```bash
   docker exec -it websocket_client bash
   python websocket_client.py
   ```

2. You'll be given a choice of **four input modes**:
   - **1. Microphone input**: Streams live audio from mic to the server.
   - **2. Single audio file**: Send a pre-recorded audio file (WAV or MP3).
   - **3. Directory**: Send all audio files from a specified folder.
   - **4. Exit**: Close the client.

3. For microphone input, press `1`. To quit the live streaming, press `q` during recording.

4. For audio files, press `2` or `3`, and provide the path when prompted. For directories, provide the folder path.

5. For exit and close the client press `4`.

### Step 4: Mounting Host Directory to Container (and Using Paths)

I’ve set it up so that a directory on local machine is shared with the container, making it easy to access files from either side.

- **Host Directory Mounting**:  
  In the `docker-compose.yml` file, I’am mounting host’s directory (`/home/tauqeer/Downloads/dataset`) to `/app/files` inside the container:
  
  ```yaml
  volumes:
    - /home/tauqeer/Downloads/dataset:/app/files
  ```

  This lets you access any files in `/home/tauqeer/Downloads/dataset` from within the container at `/app/files`.

- **Accessing Audio Files**:  
  When the client prompts you for a file or folder path, use the **container’s path** (like `/app/files`) instead of host's path.  
  - For example: If file is located at `/home/tauqeer/Downloads/dataset/sample.wav`, input `/app/files/sample.wav`.

### Step 5: Monitoring GPU Usage

Want to keep an eye on how much GPU power the server is using? You can check with:

```bash
nvidia-smi
```

This will display real-time GPU usage stats.

### File Structure

```
app/
├── client/
│   ├── Dockerfile           # Dockerfile for building the client
│   ├── requirements.txt     # Python dependencies for the client
│   ├── wait-for-it.sh       # Script for waiting for the server to be ready
│   └── websocket_client.py  # Client-side code for sending audio data
├── server/
│   ├── Dockerfile           # Dockerfile for building the server
│   ├── requirements.txt     # Python dependencies for the server
│   └── websocket_server.py  # Server-side code for receiving and analyzing audio data
├── docker-compose.yml       # Configuration file for Docker Compose
└── README.md                # Project documentation
```

### Key Features

- **Real-time audio streaming**: Stream live microphone audio.
- **File-based audio transmission**: Send WAV or MP3 files.
- **Directory-based audio transmission**: Send multiple audio files from a directory.
- **Speech quality analysis**: The server assesses the audio quality using PESQ, STOI, and SI-SDR metrics, utilizing GPU for faster performance.
- **Automatic reconnection**: The client automatically reconnects to the server if the connection drops.

### Notes

- Ensure that microphone permissions are enabled and working properly on **Ubuntu 24**.
- This project supports **WAV** and **MP3** formats. Unsupported formats will prompt a retry.
- The project uses **Python 3.12.5** and **CUDA 12.2**, so ensure that environment is compatible.

