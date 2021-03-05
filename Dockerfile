FROM python:3.9.2-alpine
ADD ./requirements.txt ./
RUN apk update \
    && apk add --no-cache gcc g++ musl-dev gfortran \
    && pip install --no-cache-dir -r requirements.txt

COPY ./app /app
CMD [ "/app/main.py" ]