FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p /var/www/public.losbarryachis.fr/public/shared

EXPOSE 5000

CMD ["python", "simple_app.py"]