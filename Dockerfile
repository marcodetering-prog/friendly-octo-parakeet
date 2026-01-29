# Craftsman Coverage Analyzer - Zero External Dependencies
FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Create necessary directories
RUN mkdir -p /app/input /app/output

# Copy application code (uses Python stdlib only)
COPY google_sheets_analyzer.py .

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import sys; sys.exit(0)" || exit 1

# Default command
CMD ["python", "google_sheets_analyzer.py"]
