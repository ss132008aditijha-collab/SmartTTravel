
FROM node:22-bookworm-slim

WORKDIR /app

# Install Python for the Flask backend
RUN apt-get update && \
    apt-get install -y --no-install-recommends python3 python3-pip python3-venv && \
    rm -rf /var/lib/apt/lists/*

# Install Node.js dependencies
COPY package*.json ./
RUN npm install

# Install Flask dependencies
COPY TrainBusBooking/requirements.txt ./TrainBusBooking/requirements.txt
RUN python3 -m venv /opt/venv

ENV PATH="/opt/venv/bin:$PATH"
ENV PYTHON_PATH="/opt/venv/bin/python"

RUN pip install --no-cache-dir -r TrainBusBooking/requirements.txt

# Copy project files
COPY . .

# Configure production environment
ENV NODE_ENV="production"
ENV DATABASE_PATH="/app/data/smarttravel.db"

# Create SQLite database directory
RUN mkdir -p /app/data

# Expose Node.js server port
EXPOSE 3000

# Initialize database and start SmartTravel
CMD ["sh", "-c", "python TrainBusBooking/database.py && npm start"]
