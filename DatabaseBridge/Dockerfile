FROM python:3.12-slim

RUN apt-get update \
    && apt-get -y install libpq-dev gcc \
    && pip install psycopg2

WORKDIR /app
RUN pip install --upgrade pip

COPY . .
RUN pip install -r requirements.txt
CMD ["python", "main.py"]