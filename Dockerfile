FROM python:3.11-slim

# Set the working directory
WORKDIR /app

# Copy the requirements first to leverage Docker cache
COPY ./src/requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the source code
COPY ./src .

# Run the server
CMD ["python3", "api_server.py"]