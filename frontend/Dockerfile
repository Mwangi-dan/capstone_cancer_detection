FROM python:3.10

WORKDIR /app

RUN apt-get update && apt-get install -y gcc build-essential

COPY requirements.txt .

# Debug line (just before the failing pip command)
RUN ls -l requirements.txt && cat requirements.txt

RUN pip install --upgrade pip
RUN pip install --default-timeout=100 --retries=10 --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["gunicorn", "app:app", "--bind", "0.0.0.0:8000"]
