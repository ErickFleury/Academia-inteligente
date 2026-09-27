# Task 38 — Facial Provider Foundation (FACE-IMPL-01)

Status: complete — foundation preflight verified. Scope: EXT-RF-FACE-01, RF-01/03/07/08, RF-20–RF-25;
RNF04–RNF06; the pilot amendments to DEC-04/05/09/10/11/12/17/18.

Read `docs/facial-access-specification.md` in full. Its owner-only, local,
no-paid-model/service scope is approved; it does not authorize live gate calls,
additional participants, or a claim of representative recognition accuracy.

## Changes

- Canonical EXT-RF-FACE-01 and its acceptance criteria in requirements.md.
- EXT-DEC-FACE-01 supporting decision; tasks 38–44 in implementation-plan.md.
- Digest-pinned CompreFace 1.2.0 Compose profile `biometrics`, isolated persistence,
  no-outbound internal provider network, loopback management port 8005.
- Backend-only provider configuration; no browser key or live turnstile adapter.
- Explicit operational `backend/scripts/biometric_preflight.py`, separate from
  automated tests: subject API, empty-subject cleanup, and blank-image rejection.

## Provider provenance and cost boundary

Inspected official CompreFace tag `v1.2.0`, commit
`d3a324aff0504b010c9f076e9a43a1fd6a50cc5c`. Its default CPU Dockerfile selects
`facenet.FaceDetector` and `facenet.Calculator`; calculator's first/default
model is `20180402-114759` (Inception ResNet v1, VGGFace2).

CompreFace is published as free software under Apache-2.0. FaceNet's upstream
software is MIT-licensed; its author distributes this pretrained checkpoint
publicly without a purchase, API subscription or usage fee, and asks for training
set attribution. The bundled MTCNN software carries its own MIT notice.
This verifies the no-cost local pilot distribution; it is not a blanket claim
that dataset/model rights for a later commercial deployment are interchangeable
with application licensing. Retain FaceNet/MTCNN and VGGFace2 attribution.

Primary sources:

- https://github.com/exadel-inc/CompreFace/tree/v1.2.0
- https://github.com/exadel-inc/CompreFace/blob/v1.2.0/LICENSE
- https://github.com/exadel-inc/CompreFace/blob/v1.2.0/embedding-calculator/Dockerfile
- https://github.com/exadel-inc/CompreFace/blob/v1.2.0/embedding-calculator/src/services/facescan/plugins/facenet/facenet.py
- https://github.com/davidsandberg/facenet#pre-trained-models
- https://github.com/davidsandberg/facenet/blob/master/LICENSE.md
- https://www.robots.ox.ac.uk/~vgg/data/vgg_face2/

Installed default model artifact: `/app/ml/.models/facenet/calculator/20180402-114759/20180402-114759.pb`.
SHA-256: `bf2c12f31880aaa865fa5a9c168dcbd619f7a40b1633f6446d416fac2421ab99`.
The artifact matches the model selected by the inspected pinned source. No model
weights or faces are copied into Git.

Initial detection/match/margin settings are 0.90/0.80/0.10 respectively. These are
explicit conservative pilot starting values, not a measured precision result or
completed calibration. Genuine webcam calibration remains owner-dependent in
Task 44; neither default provider scores nor its published LFW result substitute
for CA-21.4 verification. No real release mode exists.

## Startup and recovery

Generate `COMPREFACE_DATABASE_PASSWORD` in ignored `.env`; never commit it.
Run `docker compose --profile biometrics up -d compreface-fe`. Its dependency
chain starts the provider DB/core/API/admin. Management is available only at
`http://127.0.0.1:8005`; create the local provider owner with anonymous statistics
unchecked, create a recognition service, and save its key in ignored `.env` as
`COMPREFACE_API_KEY`. No image enrollment is necessary for service creation.

Run the operational check with:

```sh
docker compose run --rm --no-deps backend python scripts/biometric_preflight.py
```

The backend is the only app container attached to the internal provider network.
The loopback management proxy also joins a separate management bridge so Docker
can publish its localhost port; core/API/admin/provider DB remain internal-only.
The provider's separate DB and key are not the app database/Keycloak credentials.
Model files are baked into the pinned image, so runtime needs no model download.
A healthy static management page alone is not proof the recognition API is ready.
Stop the provider profile without deleting volumes to suspend it; leave
`FACIAL_ACCESS_MODE=disabled` until the later feature endpoints are ready.
Do not reset test identities in this task.

## Validation

- Docker Compose schema validation: passed.
- Operational command lint: passed.
- Provider subject list, empty-subject creation/deletion, and blank capture
  rejection: passed in 0.546 seconds, with no facial enrollment.
- Runtime status: `facenet.Calculator` and `facenet.FaceDetector` only; optional
  plugins disabled. Provider logging reduced before any enrollment.
- Provider database `allow_statistics`: false.
- Recognition worker outbound probe: OS error 101 (network unreachable).
- Provider/model version and exact artifact SHA-256 recorded above.
- Git diff whitespace/scope review passed; no credentials or captures staged.

No foundation blocking issue remains. Webcam capture, calibration, genuine-face
latency, and owner enrollment belong to later UI/integration verification; this
foundation task uses no real facial captures.
