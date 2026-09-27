"""Explicit local-provider preflight; never part of the automated test suite.

Run only against the isolated pilot deployment. Does not capture/enroll a face,
print secrets or list subject identifiers. Creates/deletes an empty random subject
and sends a generated blank image to verify controlled no-face rejection.
"""

import io
import json
import os
import time
import uuid
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from PIL import Image


def main() -> None:
    base = os.environ.get("COMPREFACE_URL", "http://compreface-api:8080").rstrip("/")
    key = os.environ.get("COMPREFACE_API_KEY", "")
    if not key:
        raise SystemExit("Preflight needs a configured provider key; no key is printed.")

    def call(method: str, path: str, data: bytes | None = None,
             content_type: str = "application/json") -> tuple[int, dict]:
        request = Request(base + path, data=data, method=method,
                          headers={"x-api-key": key, "Content-Type": content_type})
        try:
            with urlopen(request, timeout=10) as response:
                raw = response.read(65536)
                return response.status, json.loads(raw) if raw else {}
        except HTTPError as error:
            # Deliberately do not print a raw provider response.
            return error.code, {}

    prefix = "/api/v1/recognition"
    start = time.monotonic()
    code, _ = call("GET", prefix + "/subjects")
    assert code == 200, f"Subject API check failed (HTTP {code})"
    subject = "preflight-" + uuid.uuid4().hex
    try:
        code, _ = call("POST", prefix + "/subjects", json.dumps({"subject": subject}).encode())
        assert code in (200, 201), f"Empty subject creation failed (HTTP {code})"
    finally:
        code, _ = call("DELETE", prefix + "/subjects/" + subject)
        assert code in (200, 204, 404), f"Subject cleanup failed (HTTP {code})"

    buffer = io.BytesIO()
    Image.new("RGB", (128, 128), "black").save(buffer, format="PNG")
    boundary = uuid.uuid4().hex
    body = (f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; "
            f"filename=\"capture.png\"\r\nContent-Type: image/png\r\n\r\n").encode()
    body += buffer.getvalue() + f"\r\n--{boundary}--\r\n".encode()
    code, result = call("POST", prefix + "/recognize", body,
                        "multipart/form-data; boundary=" + boundary)
    assert code in (400, 422) or (code == 200 and result.get("result") == []), (
        f"Blank capture was not a controlled no-face result (HTTP {code})"
    )
    print(json.dumps({"subject_api": "passed", "empty_subject_lifecycle": "passed",
                      "blank_capture_rejected": True, "face_enrolled": False,
                      "elapsed_seconds": round(time.monotonic() - start, 3)}))


if __name__ == "__main__":
    main()
