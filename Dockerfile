FROM python:3.7.4-stretch

RUN mkdir /tmp/avatars
WORKDIR /opt/app

COPY ./autoreload.py ./
COPY ./collage_maker/requirements.txt ./requirements.txt

RUN pip install --no-cache-dir -r ./requirements.txt

COPY ./collage_maker ./collage_maker

CMD python -u autoreload.py './collage_maker' 'python -m collage_maker'