FROM python:3.11-slim

# Set the working directory
WORKDIR /app

# Copy the requirements first to leverage Docker cache
COPY ./scripts/requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the scripts
COPY ./scripts .

# Run the server
CMD ["python3", "api_server.py"]