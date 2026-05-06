FROM debian:bookworm-slim

# Set working directory
WORKDIR /app

# Copy dependency files first for efficient rebuilds
COPY requirements.txt ./

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source
COPY . /app

# Expose backend port
EXPOSE 8000

# Default command to run the server
CMD ["python", "-m", "uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8000"]
