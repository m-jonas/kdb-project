# Debian based lighweight python
FROM python:3.9-slim

# 1. System Dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    unzip \
    rlwrap \
    && rm -rf /var/lib/apt/lists/*

# 2. Setup KDB+
COPY q /opt/q
ENV QHOME=/opt/q
ENV PATH=$PATH:/opt/q/l64

# 3. Install Python Dependencies
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 4. Copy Application Code
COPY . /app

# 5. Default Entrypoint
CMD ["bash"]