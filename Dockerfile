FROM python:3.13-slim

WORKDIR /app

# Copy project files
COPY requirements.txt pyproject.toml setup.py ./
COPY src/ src/
COPY anime_cli.py scraping.py config.py db.py player.py ./

# Install Python dependencies + Playwright browsers with system deps
RUN pip install --no-cache-dir -r requirements.txt \
    && playwright install --with-deps chromium \
    && rm -rf /var/lib/apt/lists/*

# Create a non-root user
RUN useradd -m -u 1000 appuser
USER appuser

ENV PYTHONUNBUFFERED=1

ENTRYPOINT ["python", "anime_cli.py"]
