#!/bin/bash
# Apply the approved recovery settings to an existing realm without reimporting it.
set -eu
recovery_config=$(mktemp /tmp/academia-recovery-admin.XXXXXX)
trap 'rm -f "$recovery_config"' EXIT
recovery_password=${KC_BOOTSTRAP_ADMIN_PASSWORD:-}
if [ -z "$recovery_password" ] && [ -r /run/secrets/keycloak_admin_password ]; then
  recovery_password=$(cat /run/secrets/keycloak_admin_password)
fi
: "${KC_BOOTSTRAP_ADMIN_USERNAME:?Missing Keycloak administrator username}"
: "${recovery_password:?Missing Keycloak administrator password}"
# No shell tracing: the temporary administrator session is removed on exit.
/opt/keycloak/bin/kcadm.sh config credentials --config "$recovery_config" \
  --server "${KEYCLOAK_ADMIN_SERVER:-http://localhost:8080}" --realm master \
  --user "$KC_BOOTSTRAP_ADMIN_USERNAME" --password "$recovery_password" >/dev/null
# kcadm performs its default read/merge/write; keep all other realm attributes.
/opt/keycloak/bin/kcadm.sh update "realms/${KEYCLOAK_REALM:-academia}" \
  --config "$recovery_config" -s resetPasswordAllowed=true \
  -s 'attributes."actionTokenGeneratedByUserLifespan.reset-credentials"="900"'
printf '%s\n' 'Login password recovery enabled with a 15-minute link lifetime.'
