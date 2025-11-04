FROM python:3.10

RUN apt-get update && apt-get install -y wget unzip libx11-xcb1 libnss3 libxcomposite1 libxcursor1 \
    libasound2 libatk1.0-0 libatk-bridge2.0-0 libcups2 libxkbcommon0 libxrandr2 libgbm1

WORKDIR /app
COPY . /app

RUN pip install --upgrade pip
RUN pip install -r requirements.txt

RUN playwright install --with-deps chromium

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "7860"]
