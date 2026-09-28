#!/bin/bash
set -eu
# Never print these values or enable shell tracing.
export KC_DB_PASSWORD="$(cat /run/secrets/keycloak_db_password)"
export KC_BOOTSTRAP_ADMIN_PASSWORD="$(cat /run/secrets/keycloak_admin_password)"
exec /opt/keycloak/bin/kc.sh "$@"
