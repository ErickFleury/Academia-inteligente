#!/bin/bash
set -eu
app_password="$(cat /run/secrets/app_db_password)"
identity_password="$(cat /run/secrets/keycloak_db_password)"
# Preparation generates hex passwords; fail closed rather than interpolating arbitrary SQL.
[[ "$app_password" =~ ^[a-f0-9]{64}$ && "$identity_password" =~ ^[a-f0-9]{64}$ ]]
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname postgres <<SQL
CREATE USER academia_app WITH PASSWORD '$app_password' NOSUPERUSER NOCREATEDB NOCREATEROLE;
CREATE DATABASE academia OWNER academia_app;
REVOKE ALL ON DATABASE academia FROM PUBLIC;
CREATE USER academia_identity WITH PASSWORD '$identity_password' NOSUPERUSER NOCREATEDB NOCREATEROLE;
CREATE DATABASE keycloak OWNER academia_identity;
REVOKE ALL ON DATABASE keycloak FROM PUBLIC;
SQL
