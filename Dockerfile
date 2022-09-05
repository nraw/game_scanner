FROM artifacts.intranet.mckinsey.com/dockerhub/python:3.10-buster

RUN apt-get update -y && apt-get install -y \
  tmux \
  tree \
  vim \
  && rm -rf /var/lib/apt/lists/*

# making stdout unbuffered (any non empty string works)
ENV PYTHONUNBUFFERED="thisistheway"

# fix encoding issues
ENV LC_ALL=C.UTF-8
ENV LANG=C.UTF-8

# install python specific packages because you need them

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . app
WORKDIR app

