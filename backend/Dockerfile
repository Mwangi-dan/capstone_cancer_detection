FROM python:3.10

WORKDIR /app

# Install system-level dependencies (can be cached if unchanged)
RUN apt-get update && apt-get install -y gcc build-essential libgl1

# Copy and install Python dependencies early (to cache this step)
COPY requirements.txt .
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of your app (this is the only step that changes often)
COPY . .

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
