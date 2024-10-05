# Base image with CUDA 12.2 support and cuDNN
FROM nvidia/cuda:12.2.0-runtime-ubuntu22.04

# Install system dependencies for torchaudio and other libraries
RUN apt-get update && apt-get install -y \
    build-essential \
    libsndfile1-dev \
    python3-pip \
    python3-venv \
    && rm -rf /var/lib/apt/lists/*

# Set the working directory in the container
WORKDIR /app

# Create and activate a virtual environment
RUN python3 -m venv /opt/venv

# Make sure we use the virtual environment's Python and pip
ENV PATH="/opt/venv/bin:$PATH"

# Copy the requirements.txt file to the container
COPY requirements.txt .

# Install additional Python dependencies inside the virtual environment
RUN pip install -r requirements.txt

# Copy the rest of the application code into the container
COPY . .

# Expose port 8000 for the WebSocket server
EXPOSE 8000

# Command to run the WebSocket server using the virtual environment
CMD ["python", "websocket_server.py"]
