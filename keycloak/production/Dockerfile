FROM quay.io/keycloak/keycloak:26.6.3 AS builder
ENV KC_DB=postgres KC_HEALTH_ENABLED=true KC_METRICS_ENABLED=true \
    KC_HTTP_RELATIVE_PATH=/auth KC_HTTP_MANAGEMENT_RELATIVE_PATH=/
RUN /opt/keycloak/bin/kc.sh build

FROM quay.io/keycloak/keycloak:26.6.3
COPY --from=builder /opt/keycloak/ /opt/keycloak/
COPY themes/academia /opt/keycloak/themes/academia
COPY production/start.sh /opt/keycloak/bin/academia-start.sh
ENTRYPOINT ["/bin/bash", "/opt/keycloak/bin/academia-start.sh"]
CMD ["start", "--optimized", "--import-realm"]
