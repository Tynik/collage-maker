FROM python:3.7.4-stretch

WORKDIR /opt/app
COPY ./api/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r ./requirements.txt
COPY ./api ./api

ENV FLASK_APP=/opt/app/api/app.py

CMD uwsgi --ini ./api/uwsgi.ini