FROM python:3.9-slim-buster

# Install system dependencies
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    unzip \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install latest stable Chrome
RUN wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add - \
    && echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google.list \
    && apt-get update \
    && apt-get install -y google-chrome-stable \
    && rm -rf /var/lib/apt/lists/*

# Install matching ChromeDriver version
RUN CHROME_VERSION=$(google-chrome --version | awk '{ print $3 }' | awk -F'.' '{ print $1 }') \
    && CHROMEDRIVER_VERSION=$(curl -s "https://chromedriver.storage.googleapis.com/LATEST_RELEASE_$CHROME_VERSION") \
    && wget -q -O /tmp/chromedriver.zip https://chromedriver.storage.googleapis.com/${CHROMEDRIVER_VERSION}/chromedriver_linux64.zip \
    && unzip /tmp/chromedriver.zip chromedriver -d /usr/local/bin/ \
    && rm /tmp/chromedriver.zip

# Set display port to avoid crash
ENV DISPLAY=:99

# Copy your application
COPY . /app
WORKDIR /app

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

CMD ["python", "wikibot.py"]