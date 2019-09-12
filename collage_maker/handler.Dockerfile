FROM python:3.7.4-stretch

WORKDIR /opt/app
COPY ./autoreload.py ./
COPY ./handler/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r ./requirements.txt
COPY ./handler ./handler

CMD python -u autoreload.py './handler' 'python -m handler'