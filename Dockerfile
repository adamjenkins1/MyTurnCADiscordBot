FROM python:3.9.2-alpine
COPY ./app /app
COPY ./requirements.txt ./
RUN apk update \
    && apk add --no-cache gcc g++ musl-dev gfortran \
    && pip install --no-cache-dir -r requirements.txt

CMD [ "/app/main.py" ]