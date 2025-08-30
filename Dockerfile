FROM python:3.12

WORKDIR /app

# Some error with cryptography and rust
# ENV CRYPTOGRAPHY_DONT_BUILD_RUST=1
# RUN pip install cryptography==3.4.6

ADD requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

ADD . /app
