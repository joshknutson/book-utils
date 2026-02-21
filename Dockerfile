FROM python:3.11-slim-bookworm

# Install Calibre (conversion) and OpenJDK (for validation)
RUN apt-get update && \
    apt-get install -y calibre default-jre && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app
RUN pip install schedule epubcheck

COPY converter.py .
CMD ["python", "converter.py"]