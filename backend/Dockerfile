FROM python:3.13

WORKDIR /app

EXPOSE 8000

CMD ["sh", "-c", "pip install --no-cache-dir -r requirements.txt && python manage.py migrate && python manage.py runserver 0.0.0.0:8000"]