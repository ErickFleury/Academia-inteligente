# Changelog

## Unreleased

### Changed

- Enforced one active training-plan draft per client, regardless of whether AI
  or an instructor created it.
- Allowed the training AI to refine the client's sole draft while preserving
  approved, current, and historical versions as immutable.
- Added database-level proposal uniqueness and a migration that preserves
  legacy duplicate drafts as superseded history.
- Defined the personal-use MVP non-functional verification protocol in DEC-16.
