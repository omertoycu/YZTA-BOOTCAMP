FROM python:3.11-slim

WORKDIR /app

# WeasyPrint (Ulaşım/Konum Raporu PDF üretimi), native Pango/Cairo bağımlılıkları ister —
# saf pip install ile kurulamaz. libgdk-pixbuf paketi dağıtıma göre isim değiştiriyor
# (Debian trixie: libgdk-pixbuf-2.0-0, eski Debian/Ubuntu: libgdk-pixbuf2.0-0) — ikisi de denenir.
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpango-1.0-0 libpangocairo-1.0-0 libcairo2 \
    libffi-dev shared-mime-info fonts-dejavu-core \
    && (apt-get install -y --no-install-recommends libgdk-pixbuf-2.0-0 \
        || apt-get install -y --no-install-recommends libgdk-pixbuf2.0-0) \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN chmod +x entrypoint.sh

CMD ["./entrypoint.sh"]
