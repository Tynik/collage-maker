FROM python:3.7.4-stretch

WORKDIR /opt/app
COPY ./autoreload.py ./
COPY ./cm/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r ./requirements.txt
COPY ./cm ./cm

CMD python -u autoreload.py './cm' 'python -m cm'