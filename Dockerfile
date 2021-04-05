FROM python:3.9.2-slim
ADD ./requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY ./app /app
ENTRYPOINT [ "/app/main.py" ]