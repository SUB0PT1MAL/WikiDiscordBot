FROM python:3.9-slim-buster

# Install system dependencies
RUN apt-get update && apt-get install -y \
    wget \
    firefox-esr \
    && rm -rf /var/lib/apt/lists/*

# Install geckodriver
RUN GECKODRIVER_VERSION=$(curl -s https://api.github.com/repos/mozilla/geckodriver/releases/latest | grep tag_name | cut -d '"' -f 4) \
    && wget https://github.com/mozilla/geckodriver/releases/download/$GECKODRIVER_VERSION/geckodriver-$GECKODRIVER_VERSION-linux64.tar.gz \
    && tar -xvzf geckodriver-$GECKODRIVER_VERSION-linux64.tar.gz \
    && chmod +x geckodriver \
    && mv geckodriver /usr/local/bin/ \
    && rm geckodriver-$GECKODRIVER_VERSION-linux64.tar.gz

# Set display port to avoid crash
ENV DISPLAY=:99

# Copy your application
COPY . /app
WORKDIR /app

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

CMD ["python", "wikibot.py"]