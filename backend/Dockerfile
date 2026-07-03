FROM python:3.11-slim

WORKDIR /app

# WeasyPrint (Ulaşım/Konum Raporu PDF üretimi), native Pango/Cairo bağımlılıkları ister —
# saf pip install ile kurulamaz.
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpango-1.0-0 libpangocairo-1.0-0 libcairo2 libgdk-pixbuf2.0-0 \
    libffi-dev shared-mime-info fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN chmod +x entrypoint.sh

CMD ["./entrypoint.sh"]
