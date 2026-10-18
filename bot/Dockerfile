FROM python:3.11-slim
WORKDIR /app
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
RUN pip install --no-cache-dir requests==2.32.3
# o bot usa extrator/ufs.py (nomes dos estados); o resto do extrator não entra na imagem
COPY extrator/__init__.py extrator/ufs.py extrator/
COPY bot/*.py bot/
RUN useradd --uid 1000 --create-home bot && mkdir -p /app/data && chown bot /app/data
USER bot
CMD ["python", "-m", "bot.main"]
