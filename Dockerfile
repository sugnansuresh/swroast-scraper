# Use an official lightweight Python image
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set working directory
WORKDIR /app

# Install OS dependencies for Chrome and Selenium
RUN apt-get update && apt-get install -y \
    wget gnupg unzip curl xvfb libxi6 libgconf-2-4 \
    default-jdk libnss3 libxss1 libasound2 libatk1.0-0 libatk-bridge2.0-0 libgtk-3-0 \
    && apt-get clean

# Install Chrome
RUN curl -sSL https://dl.google.com/linux/linux_signing_key.pub | apt-key add - && \
    echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google-chrome.list && \
    apt-get update && apt-get install -y google-chrome-stable

# Install Python dependencies
COPY requirements.txt .
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# Copy all app files
COPY . .

# Run the main script
CMD ["python", "sw_scraper.py"]
