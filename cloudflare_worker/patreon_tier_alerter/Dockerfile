# 1. Base Image
FROM python:3.10-slim-bullseye

# 2. Set Working Directory
WORKDIR /app

# 3. Copy Application Files (requirements.txt first for layer caching)
COPY requirements.txt .

# 4. Install Dependencies
RUN pip install --no-cache-dir -r requirements.txt

# 5. Copy Remaining Application Code
COPY src/ ./src/
COPY config/ ./config/

# 6. Set Command (CMD)
CMD ["python", "src/alerter.py"]
