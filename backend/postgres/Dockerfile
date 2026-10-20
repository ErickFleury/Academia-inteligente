FROM postgres:18.6-bookworm

# Preserve the approved PostgreSQL patch version while adding the selected extension.
RUN apt-mark hold postgresql-18 \
    && apt-get update \
    && apt-get install --no-install-recommends -y postgresql-18-pgvector=0.8.7-1.pgdg12+1 \
    && rm -rf /var/lib/apt/lists/*
