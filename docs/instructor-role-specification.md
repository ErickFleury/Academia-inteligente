# Instructor Role Specification

This document provides the detailed feature narrative supporting
`EXT-RF-INST-01` through `EXT-RF-INST-05`. `docs/requirements.md` remains the
canonical implementation specification. If this narrative conflicts with the
canonical requirements or `EXT-DEC-INST-01`, implementation must stop for a
human decision.

## 1. Purpose

The `instructor` role is a dedicated professional training role with its own frontend area.

Its primary responsibilities are:

- reviewing and approving training-plan drafts;
- editing training plans before approval;
- editing already-approved training plans through the established draft/approval workflow;
- creating a first training-plan draft for a client when appropriate;
- completing and updating client onboarding data;
- searching and filtering clients by training/onboarding state;
- viewing all currently approved plans;
- viewing the plans for which the instructor is currently responsible;
- viewing the gym equipment catalog and changing the separately persisted
  operational state of individual equipment units;
- viewing the existing client social feed in read-only mode.

The instructor role is not an administrative-account-management role.

The feature depends on RF-07/RF-08. An instructor is an active local Employee
linked to Account and provisioned with the Keycloak `instructor` role. The same
Account may also own a Client profile when normalized e-mail and CPF match;
client and employee active states and permissions remain independent.

## 2. Instructor Frontend Area

The instructor must have a dedicated authenticated frontend area using the established application design system and SPA navigation.

The main navigation must contain:

1. **Feed**
2. **Planos pendentes**
3. **Meus planos**
4. **Todos os planos**
5. **Clientes**
6. **Equipamentos**
7. **Perfil**

There is no separate dashboard/home tab.

After instructor login, the default destination is **Feed**.

The **Perfil** tab is reserved for a later implementation of instructor social profiles. This specification does not require implementation of the complete instructor social-profile feature.

## 3. Feed

The instructor frontend reuses the already-implemented social feed.

For the current instructor-role implementation, the feed is **read-only**.

It includes only moderation-visible posts authored by public client profiles.
Posts restricted by a private client profile are not visible because an
instructor has no client follow identity.

The instructor may:

- view client posts that are visible under the existing feed/privacy rules;
- open permitted post detail;
- navigate through the existing feed presentation where applicable.

The instructor may not currently:

- create posts;
- comment;
- like or unlike posts;
- use a client social identity.

Instructor participation in social interactions is deferred until instructor social profiles are implemented.

No second or instructor-specific feed implementation should be created.

## 4. Pending Training Plans

### 4.1 Visibility

The **Planos pendentes** tab shows all currently pending training-plan drafts that require instructor approval.

The list is not restricted by instructor assignment.

Any instructor may review any pending draft.

A client has at most one instructor-editable training-plan draft across initial
AI generation, instructor creation, editing the current plan, and a
client-accepted AI adaptation. A retained adaptation source/history record is
not a second editable draft and must use the sole-draft boundary when it enters
instructor review. Existing drafts are never silently replaced.

AI-generated work remains draft/proposal material until approved by an instructor.

### 4.2 Pending-plan presentation

Each pending plan should show enough information for the instructor to identify and review it, including:

- client name;
- draft creation/update information;
- draft origin, such as AI-generated or instructor-created;
- current responsible instructor when a currently approved plan already exists and that information is relevant.

Each pending plan provides two primary actions:

- **Editar e aprovar**
- **Aprovar**

### 4.3 Direct approval

`Aprovar` approves the draft without requiring edits.

After approval:

- the approved plan becomes the client's current approved plan according to the existing training-plan lifecycle;
- the instructor who approves it becomes the responsible instructor for the newly approved current plan;
- the client's frontend must show the responsible instructor;
- the client's frontend must show the new approval date.

### 4.4 Edit and approve

`Editar e aprovar` opens the training-plan editing interface.

The instructor may modify the draft using the existing training-plan fields and then explicitly approve it.

Saving intermediary edits must not silently activate the plan.

The active plan changes only after the instructor explicitly completes the approval action.

### 4.5 Concurrency

If multiple instructors act on the same draft concurrently, the first successful state-changing approval/update wins.

Later actions based on stale state must not silently overwrite the newer draft/approval state.

The instructor must be required to reload/review the current state before continuing.

## 5. Approved Plan Editing

Any instructor may edit any currently approved training plan.

Editing an approved plan does not directly mutate the currently approved plan while the instructor is still working.

The edit flow uses the established draft/approval process.

When the instructor finishes the changes, the instructor must explicitly approve the edited draft before it replaces the active plan.

### 5.1 Existing draft conflict

If a client already has an existing draft and an instructor chooses to edit the current approved plan, the UI must not silently replace the existing draft.

The instructor must be asked whether to discard the existing draft and create a new draft from the current approved plan.

Only after explicit confirmation may the existing draft be replaced.

### 5.2 Approval history

When an edited draft is approved:

- it replaces the previous active plan as the current approved plan;
- the previous approved plan is retained as historical, read-only plan history;
- the newly approving instructor becomes the responsible instructor for the current plan;
- the new approval timestamp becomes the current approval timestamp.

Historical approved plans retain their historical attribution.

## 6. Responsible Instructor

The responsible instructor for the current plan is the instructor who most recently approved the current active plan.

Example:

- João approves the current plan.
- Maria later edits the plan through the draft workflow and approves the new result.
- Maria becomes the responsible instructor for the current plan.
- João remains associated with the previous historical approved plan.

The client-facing current-plan view must show:

- responsible instructor name;
- approval date.

Instructor profile-photo presentation may be added later together with instructor social-profile support. It is not a mandatory part of the current instructor-role implementation.

## 7. Meus Planos

The **Meus planos** tab shows current approved plans whose current responsible instructor is the logged-in instructor.

Each item must identify the owning client.

The instructor can:

- open the current approved plan;
- edit it through the approved-plan edit workflow;
- inspect historical approved versions associated with the plan/client.

Historical versions are read-only.

The tab should focus on currently responsible plans by default while allowing plan history to be inspected inside the relevant plan view.

## 8. Todos os Planos

The **Todos os planos** tab shows all current approved training plans in the gym, regardless of the responsible instructor.

Any instructor may open and edit any current approved plan using the same editing workflow available from `Meus planos`.

### 8.1 List information

The list should show at least:

- client;
- current responsible instructor;
- latest approval date;
- plan status.

### 8.2 Search and filters

`Todos os planos` must provide its own search/filter controls.

It must support searching by client name.

It must support filters for at least:

- responsible instructor;
- approval date or an equivalent date-range/date filtering mechanism appropriate to the existing UI conventions.

Filtering and search should be combinable.

## 9. Manual Training-Plan Creation

An instructor may create a first training plan for a client when the client does not currently have one available through the established lifecycle.

Manual creation produces a draft.

The instructor who created the draft may also approve it.

Creation and activation remain separate actions:

1. create/edit the draft;
2. explicitly approve it;
3. the approved plan becomes current;
4. the approving instructor becomes responsible for it.

If a current plan already exists, the instructor should use the edit/replacement workflow rather than create an unrelated second current plan.

## 10. Client Search Area

The **Clientes** tab provides the instructor's client-search and client-workspace functionality.

All active clients may be searched by any instructor.

There is no instructor-client assignment restriction for this feature.

### 10.1 Name search

Client search must support:

- partial-name matching;
- case-insensitive matching;
- accent-insensitive matching where practical.

Example:

`joao`

may match:

- `João Silva`
- `João Pedro`

Default result ordering is alphabetical by client name.

### 10.2 Search-result information

Each client result should expose the training/onboarding information needed by the instructor:

- client name;
- onboarding status;
- training-plan status;
- current responsible instructor, if one exists;
- draft plan, if one exists;
- current approved plan, if one exists.

Do not add account activation status as a search filter for the instructor workflow.

### 10.3 Filters

The search must support combinable filters.

At minimum:

#### Onboarding

- Todos
- Concluído
- Não concluído

#### Training plan

- Todos
- Sem plano
- Pendente de aprovação
- Plano ativo

#### Responsible instructor

- Todos
- Sem instrutor
- Eu
- Instrutor específico

Equivalent Portuguese labels may follow established application terminology.

### 10.4 Client workspace actions

Opening a client result should provide context-sensitive actions such as:

- continue/fill onboarding;
- edit completed onboarding;
- create a training-plan draft when applicable;
- open an existing draft;
- open/edit the current approved plan.

The workspace should expose the client's draft and current approved plan directly when they exist.

## 11. Instructor Onboarding Actions

An instructor may complete onboarding on behalf of a client.

The instructor may fill all onboarding fields, including the fields already permitted in the onboarding domain for health, medication, limitations, and training context.

If an unfinished onboarding draft already exists, the instructor may continue it rather than requiring a new onboarding.

### 11.1 Completed onboarding

An instructor may also edit an already-completed onboarding.

These edits update the authoritative completed onboarding directly in place.

No separate onboarding revision/version history is required by this specification.

The normal onboarding validation rules remain applicable.

Instructor access to onboarding data exists for the purpose of training-plan preparation and maintenance and should not be expanded into unrelated general-purpose sensitive-data browsing.

### 11.2 Audit attribution

Instructor-performed onboarding completion or modification must be attributable to the authenticated instructor in the system's appropriate audit/operational metadata.

No special client-facing message stating that onboarding was completed by an instructor is required.

## 12. Equipment

The **Equipamentos** tab reuses the existing equipment catalog and adds the
approved equipment-unit operational-status functionality. Inventory-active and
operational state are independent.

The instructor may:

- view equipment models;
- view individual physical units;
- view operational/out-of-order state;
- mark an individual unit as out of order;
- return an individual unit to operational state.

The instructor may not:

- create equipment models;
- create equipment units;
- edit equipment model metadata;
- delete equipment;
- perform general inventory administration outside the approved operational-status action.

### 12.1 Training usability

Equipment operational state must influence training usability.

If at least one applicable unit is active and operational, the equipment model may be considered usable for training-plan purposes.

If all applicable units are out of order, the equipment model must be considered unusable for training-plan purposes.

`Operational` does not mean `currently free`.

This remains equipment usability/inventory state, not real-time machine availability or occupancy.

## 13. Profile Tab

The instructor navigation includes a **Perfil** tab.

This destination is reserved for the future instructor social-profile implementation.

The current instructor-role implementation must not require a complete instructor social profile or profile-photo system.

The presence of the navigation destination should not be interpreted as approval to invent social-profile behavior that has not yet been specified.

## 14. Permissions Summary

### Instructor may

- search all active clients;
- inspect relevant client onboarding/training status;
- complete unfinished client onboarding;
- edit completed client onboarding;
- create a first training-plan draft where applicable;
- view all pending plan drafts;
- edit and approve pending plans;
- approve drafts directly;
- view all current approved plans;
- edit any current approved plan through the draft/approval workflow;
- view current plans for which they are responsible;
- inspect read-only historical approved plan versions;
- view the equipment catalog;
- mark an individual equipment unit out of order;
- restore an individual equipment unit to operational state;
- view the existing client social feed in read-only mode.

### Instructor may not, through this specification

- manage client accounts or authentication;
- activate/deactivate client accounts;
- create/delete equipment inventory records;
- edit general equipment-model metadata;
- bypass the draft/approval workflow when changing active plans;
- silently overwrite an existing draft when starting an edit from an active plan;
- modify historical approved plan versions;
- create social posts;
- comment on social posts;
- like/unlike social posts;
- act through a client social identity;
- receive a complete instructor social-profile implementation yet.

## 15. Frontend Navigation Summary

The instructor frontend navigation is:

```text
Feed                    ← default route
Planos pendentes
Meus planos
Todos os planos
Clientes
Equipamentos
Perfil
```

There is no separate `Início` or dashboard tab.

The frontend must reuse established application-shell, SPA, responsive, accessibility, and visual-design conventions rather than creating an unrelated instructor UI system.

## 16. Key Workflow Examples

### 16.1 Approve an AI-created draft

```text
AI-created draft
→ appears in Planos pendentes
→ instructor opens it
→ Aprovar
→ becomes current plan
→ approving instructor becomes responsible
→ client sees updated current plan + responsible instructor + approval date
```

### 16.2 Edit before approval

```text
Pending draft
→ Editar e aprovar
→ instructor modifies draft
→ explicit approval
→ becomes current plan
→ instructor becomes responsible
```

### 16.3 Edit an existing approved plan

```text
Current approved plan
→ instructor selects Editar
→ draft/edit workflow
→ instructor makes changes
→ explicit approval
→ previous approved plan retained as historical read-only
→ edited plan becomes current
→ editing/approving instructor becomes responsible
```

### 16.4 Existing draft while editing current plan

```text
Current approved plan
+
existing draft

→ instructor selects Editar
→ system warns that a draft already exists
→ instructor may explicitly discard existing draft and create a new draft from
  the current plan
→ no silent replacement
```

### 16.5 Complete onboarding

```text
Client search
→ filter "Onboarding não concluído"
→ open client
→ continue/fill onboarding
→ validate
→ complete
```

### 16.6 Edit completed onboarding

```text
Client
→ completed onboarding
→ instructor edits allowed fields
→ normal validation
→ authoritative completed onboarding updated in place
```

### 16.7 Equipment unusable

```text
Equipment model
├── Unit 1: out of order
├── Unit 2: out of order
└── Unit 3: out of order

→ equipment model is unusable for training-plan purposes
```

## 17. Future Work Explicitly Deferred

The following are acknowledged but not defined by this specification:

- full instructor social profiles;
- instructor profile-photo lifecycle tied to those profiles;
- instructor posting/commenting/liking in the social feed;
- other instructor-social-network behavior not yet approved.

Future work must extend this specification without silently redefining the training, onboarding, equipment, or client-search rules established here.
