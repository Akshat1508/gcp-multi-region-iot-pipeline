# Start with a lightweight, bare-bones Linux computer that has Python 3.11 installed
FROM python:3.11-slim

# Create a folder inside that computer called /app and move into it
WORKDIR /app

# Copy your shopping list from your Windows PC into the Linux computer
COPY requirements.txt .

# Tell the Linux computer to read the list and install the libraries
RUN pip install -r requirements.txt

# Copy the rest of your files (server.py, telemetry_pb2.py, etc.) into the computer
COPY . .

# Tell the computer what to do when it turns on: run your server!
CMD ["python", "server.py"]