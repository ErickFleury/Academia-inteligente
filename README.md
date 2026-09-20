# Academia Inteligente

Task 01 establishes the runnable foundation only; it contains no domain schema,
migrations, or business endpoints.

## Local runtime

1. Copy `.env.example` to `.env` and replace the local placeholder passwords.
2. Run `docker-compose up --build`.
3. Open the frontend at `http://localhost:5173`, API health at
   `http://localhost:8000/health`, API OpenAPI at `http://localhost:8000/docs`,
   Keycloak at `http://localhost:8080`, and Mailpit at `http://localhost:8025`.

Only the UI, API, Keycloak, and Mailpit are bound to loopback addresses.
PostgreSQL is available exclusively on the internal Compose network. Configure
UFW on the Linux host to permit only the intended public reverse-proxy/UI/API
ports; never publish PostgreSQL.

## Quality checks

Run these commands through the containers so they use the approved baseline:

```bash
docker-compose run --rm backend ruff check .
docker-compose run --rm backend ruff format --check .
docker-compose run --rm backend pytest
docker-compose run --rm frontend npm run lint
docker-compose run --rm frontend npm run build
docker-compose run --rm frontend npm test
```

`docker-compose up --build` runs service health checks. To inspect them, use
`docker-compose ps`.

The frontend lockfile must be generated with the approved Node image before a
release build is used: `docker-compose run --rm frontend npm install`. This
foundation environment could not generate it because Docker daemon access was
unavailable during setup.
