# Changelog

## Unreleased

### Changed

- Added permanent administrator-led client-account erasure, removing the
  linked Keycloak identity and all client-owned application records.
- Added administrator controls to hide, restore, or tombstone shared progress
  posts, including an optional moderation reason and an administration screen.
- Correctly handle empty successful API responses when completing account
  erasure.
- Enforced one active training-plan draft per client, regardless of whether AI
  or an instructor created it.
- Allowed the training AI to refine the client's sole draft while preserving
  approved, current, and historical versions as immutable.
- Added database-level proposal uniqueness and a migration that preserves
  legacy duplicate drafts as superseded history.
- Defined the personal-use MVP non-functional verification protocol in DEC-16.
- Resolved EXT-DEC-SOC-01 for controlled progress sharing: private-by-default
  posts, an active-client shared audience, and shared-only administrator
  hide/restore moderation with auditable reasons.
