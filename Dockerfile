FROM python:3.10-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PORT=7860

# Create working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY . .

# Create directory for uploads and database initialization
RUN mkdir -p uploads frontend/uploads/avatars

# Expose port (Hugging Face default)
EXPOSE 7860

# Run Flask using gunicorn
CMD gunicorn --bind 0.0.0.0:$PORT backend.app:app
