# ---- Base python ----
FROM python:3.5-alpine AS base
MAINTAINER Chirag Maliwal "cmaliwal@amsysis.com"

# ---- Dependencies ----
FROM base AS dependencies
COPY requirements.txt /
RUN pip install -r /requirements.txt

# ---- Copy Files/Build ----
FROM dependencies AS build
COPY . /src
WORKDIR /src
CMD  ["python", "app.py"]
