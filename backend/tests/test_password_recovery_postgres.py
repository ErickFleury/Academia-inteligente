import os
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest
from test_password_recovery import Provider, client
from test_training_review_postgres import sessions as sessions

from app.modules.identity.password_recovery import PasswordRecoveryError, PasswordRecoveryService

pytestmark = pytest.mark.skipif(
    os.getenv("TEST_POSTGRES") != "1", reason="Isolated PostgreSQL opt-in"
)


def test_concurrent_requests_from_both_entry_points_send_only_one_email(sessions):
    with sessions() as session:
        target_id = client(session).id
    barrier = Barrier(2)
    provider = Provider()
    service = PasswordRecoveryService(provider)

    def send(index):
        with sessions() as session:
            barrier.wait(timeout=10)
            try:
                if index:
                    service.request_for_subject(session, "ada")
                else:
                    service.request_for_client(session, target_id)
                return 200
            except PasswordRecoveryError as error:
                return error.status

    with ThreadPoolExecutor(max_workers=2) as workers:
        results = list(workers.map(send, range(2)))
    assert sorted(results) == [200, 429]
    assert len(provider.calls) == 1
