FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN python manage.py collectstatic --noinput

EXPOSE 3000

CMD ["gunicorn", "eztax.wsgi:application", "--bind", "0.0.0.0:3000", "--workers", "2"]
