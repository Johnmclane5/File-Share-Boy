FROM python:3.9


ENV DEBIAN_FRONTEND=noninteractive
RUN apt -qq update
COPY . /app
WORKDIR /app
RUN chmod 777 /app

RUN pip3 install --no-cache-dir -r requirements.txt

CMD sh start.sh
