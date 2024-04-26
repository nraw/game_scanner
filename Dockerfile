FROM python:3.12-slim

WORKDIR /app

ADD requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

ADD . /app
