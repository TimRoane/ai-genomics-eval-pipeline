FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    bcftools samtools tabix \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY . .
RUN pip install -e ".[dev]"

CMD ["genomics-eval", "--help"]
