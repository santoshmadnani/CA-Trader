FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1     PYTHONUNBUFFERED=1     CA_TRADER_DATA_DIR=/app/data

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py .
COPY terminal.html .
COPY CA_Trader_Login.html .
COPY fitness.html .
COPY terminal_selector.html .
COPY ca_trader_guide.html .
COPY static/ static/
COPY backend/ backend/

RUN mkdir -p /app/data

EXPOSE 8000

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
