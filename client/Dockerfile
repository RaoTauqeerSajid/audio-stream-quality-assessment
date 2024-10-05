# Use the official Python image as the base image
FROM python:3

# Install system dependencies (needed for PyAudio, ALSA, and gcc)
RUN apt-get update && apt-get install -y \
    libasound-dev \
    alsa-utils \
    libportaudio2 \
    libportaudiocpp0 \
    portaudio19-dev \
    ffmpeg \
    gcc \
    pulseaudio \
    && apt-get clean

# Set the working directory in the container
WORKDIR /app

# Copy the requirements.txt file to the container
COPY requirements.txt .

# Install the Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the wait-for-it script into the container
COPY wait-for-it.sh /app/wait-for-it.sh

# Ensure the wait-for-it.sh script has execution permissions
RUN chmod +x /app/wait-for-it.sh

# Copy the rest of the application code into the container
COPY . .

# Command to run the WebSocket client
CMD ["python", "websocket_client.py"]
