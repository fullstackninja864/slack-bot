FROM python:3.5
MAINTAINER Chirag Maliwal "chiragmaliwal1995@gmail.com.com"

COPY requirements.txt /
RUN pip install -r /requirements.txt

ADD . /src
WORKDIR /src
CMD  ["python", "app.py"]
