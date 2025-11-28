FROM python:3.9-slim

RUN apt-get update && apt-get install -y iperf3 ca-certificates && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 5000

ENV PYTHONUNBUFFERED=1

CMD ["python", "app.py"]

