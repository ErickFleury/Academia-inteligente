# Academia Inteligente — Frontend Design Direction

**Status:** approved visual direction (2026-09-21). This document governs the
application's visual/UI language. Product behavior and authorization remain
governed by `docs/requirements.md` and `docs/decisions.md`.

**Reference:** [Strive Gym Club](https://www.strivegymclub.com/) is inspiration
for confident type, strong contrast, broad visual sections, restrained accents,
and fitness imagery. This project uses its own brand, layout decisions, copy,
code, and assets. Do not copy the reference's source, logo, text, images, exact
palette, or page composition.

## Principles

- Athletic, modern, premium, direct, and energetic without decoration for its
  own sake. Preserve information clarity in operational and sensitive screens.
- Use one React/MUI design system for public, client, and admin experiences.
  Client pages may have more visual space and imagery; admin pages use the same
  tokens with denser tables, lists, and forms.
- Establish shared foundations in Task 08 before building more client screens.
  Task 18 checks consistency after major MVP screens exist.

## Language and copy

- Follow EXT-RF-LANG-01 in `docs/requirements.md`: application-controlled UI
  copy is Brazilian Portuguese (`pt-BR`) across public, client, and admin areas.
  Keep this design document, task prompts, source identifiers, and API contracts
  in English. Do not translate user-authored text or proper names.
- Cover headings, navigation, buttons, form labels/help, validation, loading,
  empty, success, error and authorization states, dialogs, toasts, document
  titles, accessible names, and in-app AI onboarding/training responses. Do not
  surface raw English provider errors to users.
- Use appropriate `pt-BR` presentation of dates, times, numbers, and currency
  where displayed. Keep established English gym or technical terms such as
  “bulking” when they are clearer than an artificial translation.
- Reuse shared wording and formatting helpers where available. Check real
  phone, tablet, and desktop flows for unintended English copy; language
  changes must not weaken validation, privacy, or accessibility.

## Tokens and foundations

- **Typography:** Use a freely available or system-compatible sans-serif
  strategy; do not add paid/proprietary fonts. Define display, page title,
  section title, body, label, caption, and compact admin-data roles in the MUI
  theme. Large/display headings may use uppercase selectively. Forms, health
  text, training instructions, chat, and tables use readable mixed case.
- **Semantic color:** Start from an original ink/chalk/coral direction, not
  Strive's exact values. Suggested dark tokens: background `#10181B`, surface
  `#1B272B`, elevated surface `#26363B`, primary text `#F5F7F4`,
  secondary text `#B7C5C6`, accent `#FF8564`, accent contrast
  `#172024`, border `#405157`, success `#85D8AD`, warning
  `#F5C968`, error `#FF9A91`, info `#90CBE9`. A light admin content
  surface may use background `#F2F4F1`, surface `#FFFFFF`, primary text
  `#172024`, secondary text `#4D5E62`, and a deeper accent for text/icons.
  Verify actual combinations against contrast requirements before shipping.
  Status and validation always include words/icons, never color alone.
- **Spacing and shape:** Use the MUI 8 px rhythm with smaller 4 px increments
  only when needed. Establish container widths, section spacing, card padding,
  border radii, borders, and restrained elevation as reusable tokens. Prefer
  coherent grouped sections over many unrelated cards or one-off values.
- **Component hierarchy:** Define consistent primary/secondary/quiet and
  destructive button styles; text fields, selects, checkboxes, radios,
  switches, chips/badges, cards, dialogs, alerts, snackbars/toasts,
  skeletons/progress indicators, empty/error states, page/section headers,
  responsive containers, and navigation. Reuse MUI theme overrides and shared
  components before adding local style rules. Do not add another UI framework.

## Layout and interaction

- **Public/entry:** A bold but simple brand header, concise orientation, and
  unmistakable primary sign-in action. Auth callback, expired session,
  unauthorized route, loading, and error states belong to the same system.
  The Keycloak-hosted credential page is outside the React presentation scope,
  but login and first-access screens shown to users must still be in Portuguese.
  Prefer supported locale configuration; a custom theme, if needed, requires a
  separately scoped integration task.
- **ClientShell:** Reusable authenticated navigation, page header, main action,
  content width, responsive sections, and feedback. On phone, prioritize the
  current client action and touch navigation instead of shrinking desktop
  columns. Planned destinations include home, onboarding, training, AI,
  progress, equipment, occupancy/presence, and profile when implemented.
- **AdminShell:** Same type family, accent, controls, and feedback, with denser
  client search/list/detail/edit and status views. Make account state and
  provisioning/invitation outcomes legible; retain clear action hierarchy.
  Confirmation UI is used for genuinely consequential actions as approved by
  the owning workflow, not added as a new business rule by styling alone.
- **Onboarding:** Invitation entry leads into a deliberate client journey.
  Group physical and health fields into understandable sections/steps; show
  required/optional status and validation plainly. Conversation and structured
  progress coexist without visualizing health information sensationally.
  Completion has a concise review and clear action.
- **Training:** Current plan is optimized for use during a workout on a phone:
  session → exercise → sets/repetitions/time/load/rest → instructions. Group
  related values rather than giving every value a separate card. Review,
  proposal, approved, and history states remain distinct where approved.
- **AI chat:** Shared client-shell language with clear sender distinction,
  readable message width, persistent input, generating/error/retry states, and
  structured message content when required. Context cues should help without
  crowding the conversation. Reuse chat primitives across onboarding and
  training chat; adaptation adds states to them.
- **Later modules:** Progress sharing uses a restrained fitness-feed layout
  with author, time, content, and own-post visibility. Equipment can use local
  imagery, name/type, concise metadata, detail, and total active units.
  Occupancy presents a prominent anonymous count; opt-in named presence is a
  separate view with its own consent state.

## Imagery, responsiveness, and accessibility

- Use only project-owned, licensed, or explicitly approved local imagery.
  Fitness photography may support entry, client home, equipment, and selected
  empty/header states. Never reuse Strive assets or rely on random external
  image URLs. Content and actions work when an image is absent. Health forms
  and dense admin tables should not gain decorative imagery.
- Check representative phone, tablet, and desktop layouts for every UI task.
  Client flows must avoid ordinary horizontal scrolling and keep touch targets,
  actions, inputs, and navigation usable. Exact formal test viewports remain
  subject to DEC-16.
- Preserve semantic headings/landmarks, labels, keyboard access, visible
  focus, screen-reader-compatible controls, validation text, readable sizes,
  disabled states, and adequate text/control contrast. Recheck RNF02/RNF03
  whenever layouts change.

## Reuse and verification

Task 08 creates the theme, shared UI primitives, ClientShell/AdminShell, and
retroactively restyles the frontend delivered by Tasks 01–07 while preserving
their behavior and API contracts. Future UI tasks must inspect and reuse these
pieces; a genuinely new pattern should be added to the shared system with its
states documented here. Task 18 performs a final MVP visual/accessibility
pass after the major screens are implemented; Task 19 verifies the integrated
MVP. Design work alone does not satisfy RF/CA or formal RNF criteria.
