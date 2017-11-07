FROM python:2.7

RUN ["apt-get", "update"]
RUN ["apt-get", "install", "-y", "portaudio19-dev"]

WORKDIR /libsoundannotator

COPY requirements.txt .

RUN pip install -r requirements.txt

COPY libsoundannotator libsoundannotator
COPY README .
COPY setup.py .

RUN python setup.py build test install