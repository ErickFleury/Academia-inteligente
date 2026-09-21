# Academia Inteligente — Canonical Implementation Requirements

This is the primary consolidated specification for future implementation. It
preserves every original identifier and acceptance criterion while integrating
approved decisions and explicitly labeled product extensions. The historical
source specification is preserved unchanged at `requirements.md`.

**Original source:** `requirements.md`, derived from
`Codex-Requisitos (teste academia)(1).docx`, Universidade Federal de Goiás,
Engenharia de Computação, EMC, September 2026.

**Coverage:** all 33 original functional requirements and 110 functional
acceptance criteria, 6 non-functional requirements and 18 non-functional
acceptance criteria, 37 business rules, 10 technology entries, 18 original DEC
questions, approved chronological decisions, and 4 approved product-extension
requirements.

**Authority and conflict order:**

1. `requirements.md` remains the authoritative historical/source statement of
   original RF/CA/RNF/RN/TEC/DEC content.
2. `docs/decisions.md` is the authoritative chronological record of approved
   resolutions and interpretations.
3. `docs/product-extensions.md` is the authoritative record of approved
   additions beyond the original specification.
4. This document consolidates those sources for implementation. If they appear
   to conflict, use an explicit approved decision; otherwise stop the affected
   task and request a human decision.
5. `docs/implementation-plan.md` and `docs/tasks/` define execution order and
   verified status, but do not create product requirements by themselves.

Unchecked acceptance boxes preserve source traceability; they are not evidence
that a criterion is unimplemented or failed. Current verified status appears in
section 11 and is based only on completed tasks and test evidence.

## 1 Contexto e orientação de uso

### 1.1 Product purpose and vision

Centralize and automate gym administrative, financial, and service operations,
improving establishment control and the preparation of client-specific training
plans. The system is both an administrative platform and a client-facing gym
application.

The domain includes client and employee registration, authentication and
permissions, onboarding, training plans and AI interactions, biometrics and
physical access, attendance and occupancy, charges and plans, administrative
indicators, classes, equipment, and the approved limited client-facing
extensions.

The intended client journey is:

`registration → Keycloak provisioning → secure credential setup → login → local
client resolution → personal area → onboarding → training-plan generation →
current-plan view → AI assistant → later client modules`.

Later modules may include occupancy, equipment, financial/agenda functions,
progress sharing, and opt-in visible presence according to their own scope and
decision gates. This journey expresses dependencies; it does not move every
stage into the original MVP.

### 1.2 Como interpretar este documento

O anexo informa que parte dos requisitos ainda pode não ser necessária, estar classificada incorretamente ou divergir do que foi solicitado pelo professor. Ele não identifica individualmente todos esses casos. Por isso, os itens foram preservados e os conflitos foram registrados na seção 9. A presença de um item neste arquivo não significa que ele pertence automaticamente à próxima entrega.

| Identificador | Significado |
| --- | --- |
| RF-01 a RF-33 | Requisitos funcionais do anexo; RF-24X e RF-25X conservam o sufixo original. |
| CA-XX.Y | Critério de aceitação associado ao requisito funcional original. |
| RNF01 a RNF06 | Requisitos não funcionais, com a numeração original. |
| CA-RNFXX.Y | Critério de aceitação não funcional original. |
| RN-01 a RN-37 | Regras de negócio com os identificadores originais. |
| TEC-01 a TEC-10 | Identificadores adicionados para referenciar as dez entradas da tabela de tecnologias. |
| DEC-01 a DEC-18 | Original decision questions; section 9 records which are now resolved and which remain open. |
| EXT-RF-* / EXT-CA-* | Approved additions from `docs/product-extensions.md`, never original RF/CA identifiers. |

Os requisitos e critérios foram reorganizados com ajustes de grafia, sem supressão de condições. As notas de implementação, a sequência sugerida e as pendências são orientações desta consolidação e estão identificadas como tais.

### 1.3 Instruções para o Codex

1. Read this file before planning functionality and identify the affected RF,
   extension requirements, RNF, RN, decisions, and acceptance criteria.
2. Trabalhar no escopo da tarefa atual. Usar o MVP da seção 8 como referência de prioridade, respeitando suas dependências e pendências.
3. Aplicar as regras de negócio e os requisitos não funcionais pertinentes mesmo quando a tarefa mencionar apenas um RF.
4. Não transformar alternativas tecnológicas, itens condicionais ou dúvidas do anexo em decisões silenciosas. Resolver apenas as pendências que afetem a tarefa; avançar no trabalho independente delas.
5. Preservar os identificadores para permitir rastrear tarefas, alterações e validações até os requisitos.
6. Usar as caixas de aceitação como acompanhamento: marcar um item somente depois de implementá-lo e verificar seu comportamento.
7. Não ampliar o escopo por inferência de um diagrama ou pela existência de uma regra sem fluxo funcional detalhado. Registrar a necessidade e relacioná-la à decisão correspondente.
8. Follow the workflow constraints and task system in the implementation plan.
9. For client-owned protected resources, derive the local account/client from
   the authenticated Keycloak `sub`; a browser-supplied `client_id` is never
   proof of ownership.

## 2 Atores e responsabilidades mencionados

| Ator ou termo | Responsabilidade indicada no anexo |
| --- | --- |
| Cliente ou aluno | Preencher e consultar seus dados, acessar ficha e chat, comprar plano e consultar informações disponibilizadas pela academia. |
| Atendente | Realizar atividades de atendimento e cadastrar foto facial do cliente conforme permissões. |
| Instrutor, professor ou profissional | Avaliar sugestões da IA, modificar fichas e montar treinos manualmente; permanecer identificado como responsável pelo que criou ou alterou. |
| Administrador ou usuário administrativo | Executar as operações administrativas previstas, conforme autorização. |
| Funcionário | Categoria usada nos requisitos de cadastro e autorização; inclui responsabilidades que precisam ser distribuídas entre os perfis operacionais. |
| Visitante | Consultar equipamentos disponíveis, conforme RF-33. |

DEC-04 resolves the current role baseline: Keycloak realm roles are `client`,
`employee`, `attendant`, `instructor`, and `admin`; attendant and instructor are
specialized employee roles. Permissions not expressly supported below remain
undefined rather than implicitly granted.

### 2.1 Authorization matrix

| Role | Approved capability boundary |
| --- | --- |
| Client | Authenticated self-service for the client's own onboarding, current training plan, AI conversation, and later explicitly approved client features. No administrative APIs. |
| Employee | Base workforce identity only; no blanket access to health, biometric, financial, or administrative data. Concrete operations require an approved specialized permission. |
| Attendant | Employee specialization; may manage biometric enrollment when RF-22 exists, but may not access health/medical onboarding data. |
| Instructor | Employee specialization; may access health information only when functionally required for approved training-plan review/work, and remains attributable under RN-31. |
| Admin | Approved administrative operations such as client management. Admin status alone does not grant unrestricted access to health or biometric data. |
| Visitor | Only public behavior explicitly approved, currently equipment consultation under RF-33 when implemented. No protected client data. |

Backend authorization is authoritative and independent from frontend route or
control visibility. Employee/admin identities are not publicly registered: the
initial administrator is realm-bootstrapped from environment configuration,
and future employees are provisioned by an authorized employee-management flow.

### 2.2 Approved authentication and identity model

- `account.id` and `client.id` are independent application-generated UUIDs.
- `account.keycloak_subject` is the unique external Keycloak OIDC `sub`; it is
  never the account or client primary key.
- `account.email` is normalized, authoritative, and globally unique even for
  inactive accounts. It is not duplicated as an authoritative client field.
- `account.account_active` alone controls application-login eligibility. It is
  separate from enrollment/payment/biometric state and physical gym access.
- `client.account_id` is a unique foreign key, establishing one Account ↔ Client
  relationship. Client-domain data belongs to Client, not Account.
- Credentials remain exclusively in Keycloak. PostgreSQL stores no password,
  temporary password, required-action token, or authentication secret.
- Administrative client creation first persists the local Account/Client pair
  and a durable, per-client provisioning record. It reports a distinct pending
  state while an independent background reconciliation provisions one Keycloak
  identity with matching e-mail and only the `client` role, persists its `sub`,
  and starts Keycloak's secure first-access required action so the client
  defines their password. A pending client cannot authenticate, and one pending
  identity never blocks another administrative registration.
- Public self-registration is disabled. Creating a client never grants an
  administrative or employee role.
- Cross-system partial failures require explicit compensation or durable,
  idempotent reconciliation. A null-subject local account is not assumed usable.
- Protected client behavior resolves `sub → account → client` server-side and
  rejects inactive, unlinked, unauthorized, or cross-client requests.

The same Account abstraction is intended for later employee/admin identities;
it is not client-specific credential storage.

## 3 Requisitos funcionais

Os 33 requisitos abaixo mantêm a numeração e todos os critérios de aceitação do anexo. “Fora do MVP informado” significa apenas que o item não aparece na lista inicial de MVP; ele continua fazendo parte do catálogo de requisitos.

### RF-01 Cadastrar cliente

**Escopo:** MVP informado no anexo.

Permitir que um usuário administrativo registre um novo cliente e o vincule a um e-mail.

**Critérios de aceitação**

- [ ] **CA-01.1:** com os campos obrigatórios válidos, o sistema cria o cliente e gera identificador único.
- [ ] **CA-01.2:** e-mail já associado a outra conta ativa é rejeitado.
- [ ] **CA-01.3:** campos inválidos retornam mensagem de validação e nenhum cadastro parcial é criado.

### RF-02 Consultar e pesquisar clientes

**Escopo:** MVP informado no anexo.

Permitir a usuários administrativos localizar e consultar clientes cadastrados.

**Critérios de aceitação**

- [ ] **CA-02.1:** o administrador consegue listar clientes.
- [ ] **CA-02.2:** pesquisa por nome ou e-mail retorna registros correspondentes.
- [ ] **CA-02.3:** usuário sem autorização não consegue consultar dados de terceiros.

### RF-03 Atualizar e alterar estado do cliente

**Escopo:** MVP informado no anexo.

Permitir alteração dos dados cadastrais básicos e ativação/desativação do cliente.

**Critérios de aceitação**

- [ ] **CA-03.1:** alterações válidas permanecem após recarregar a página.
- [ ] **CA-03.2:** cliente desativado deixa de ser tratado como usuário habilitado.
- [ ] **CA-03.3:** desativar não apaga automaticamente seu histórico.
- [ ] **CA-03.4:** clientes habilitados precisam ter uma foto do rosto válida para a biometria.

**Nota de consolidação:** O critério CA-03.4 depende da biometria de RF-22, que não aparece no MVP informado. A relação entre cliente ativo, cliente habilitado, foto válida e pagamento precisa ser definida em DEC-05.

### RF-04 Autenticar usuário

**Escopo:** MVP informado no anexo.

Identificar cliente, funcionário ou administrador antes de permitir o acesso às áreas protegidas.

**Critérios de aceitação**

- [ ] **CA-04.1:** credenciais válidas de usuário ativo iniciam uma sessão autenticada.
- [ ] **CA-04.2:** credenciais inválidas não iniciam sessão.
- [ ] **CA-04.3:** rotas protegidas sem sessão válida retornam estado de não autenticado.

### RF-05 Autorizar funções conforme perfil

**Escopo:** MVP informado no anexo.

Separar permissões de cliente, Funcionário e Administrador.

**Critérios de aceitação**

- [ ] **CA-05.1:** cliente não acessa funções administrativas.
- [ ] **CA-05.2:** administrador acessa operações administrativas previstas.
- [ ] **CA-05.3:** tentativa de invocar diretamente uma API proibida é rejeitada, mesmo sem usar a interface.

**Nota de consolidação:** O anexo também menciona atendentes e instrutores. Detalhar suas permissões sem presumir que todos os funcionários possuem os mesmos acessos; ver DEC-04.

### RF-06 Recuperar acesso por e-mail

**Escopo:** Fora do MVP informado no anexo.

Permitir recuperação de conta vinculada ao e-mail.

**Critérios de aceitação**

- [ ] **CA-06.1:** solicitação válida gera mensagem de recuperação.
- [ ] **CA-06.2:** token expirado ou já utilizado é recusado.
- [ ] **CA-06.3:** depois da recuperação, o usuário consegue autenticar-se com o novo mecanismo/credencial.
- [ ] **CA-06.4:** o servidor SMTP deve ser isolado em um docker

**Nota de consolidação:** CA-06.4 é uma restrição técnica de implantação do serviço de e-mail, preservada aqui para rastreabilidade e também registrada na seção 6.2. A escolha entre SMTP e API de e-mail está em DEC-03.

### RF-07 Cadastrar funcionário

**Escopo:** Fora do MVP informado no anexo.

Permitir o cadastro básico de funcionários.

**Critérios de aceitação**

- [ ] **CA-07.1:** administrador consegue criar um funcionário com os dados obrigatórios.
- [ ] **CA-07.2:** o funcionário recebe identificador único.
- [ ] **CA-07.3:** duplicidade incompatível de conta/e-mail é recusada.

### RF-08 Consultar, atualizar e desativar funcionário

**Escopo:** Fora do MVP informado no anexo.

Manter dados e estado dos funcionários cadastrados.

**Critérios de aceitação**

- [ ] **CA-08.1:** administrador consegue listar e consultar funcionários.
- [ ] **CA-08.2:** alterações válidas persistem.
- [ ] **CA-08.3:** funcionário desativado perde as permissões vinculadas à conta.

### RF-09 Enviar convite de onboarding por e-mail

**Escopo:** MVP informado no anexo.

Enviar ao cliente cadastrado um e-mail contendo link para realização do primeiro onboarding.

**Critérios de aceitação**

- [ ] **CA-09.1:** ao acionar o convite, mensagem é enviada ao e-mail vinculado.
- [ ] **CA-09.2:** o link aponta para o onboarding daquele cliente.
- [ ] **CA-09.3:** falha de envio fica registrada como falha e não como conclusão.

### RF-10 Acessar onboarding por link seguro

**Escopo:** MVP informado no anexo.

Abrir o formulário a partir do link recebido por e-mail.

**Critérios de aceitação**

- [ ] **CA-10.1:** token válido abre o formulário correspondente.
- [ ] **CA-10.2:** token inválido ou expirado é rejeitado.
- [ ] **CA-10.3:** um token não permite abrir o onboarding de outro cliente.

### RF-11 Registrar dados físicos

**Escopo:** MVP informado no anexo.

Registrar os detalhes físicos previstos no formulário aprovado para orientar o treino.

**Critérios de aceitação**

- [ ] **CA-11.1:** todos os campos físicos definidos no esquema do onboarding podem ser preenchidos e persistidos.
- [ ] **CA-11.2:** campos marcados como obrigatórios são validados.
- [ ] **CA-11.3:** reabrir o formulário recupera corretamente os dados salvos enquanto ele estiver editável.

**Nota de consolidação:** O esquema aprovado, os campos obrigatórios e suas validações não estão completamente definidos; ver DEC-06.

### RF-12 Registrar medicações e condições de saúde do cliente

**Escopo:** MVP informado no anexo.

Registrar as informações médicas mencionadas na reunião, incluindo queixas, medicamentos e problemas/condições anteriores informados pelo cliente.

**Critérios de aceitação**

- [ ] **CA-12.1:** o formulário possui áreas identificáveis para queixas, medicações e histórico/problemas relevantes.
- [ ] **CA-12.2:** dados submetidos ficam associados apenas ao cliente correto.
- [ ] **CA-12.3:** usuário sem permissão não obtém essas informações por interface nem API.

### RF-13 Validar e concluir onboarding

**Escopo:** MVP informado no anexo.

Marcar o formulário como concluído quando o cliente finalizar o preenchimento necessário.

**Critérios de aceitação**

- [ ] **CA-13.1:** formulário incompleto nos campos obrigatórios não pode ser concluído.
- [ ] **CA-13.2:** ao concluir, o sistema registra estado e data/hora da conclusão.
- [ ] **CA-13.3:** a IA pode identificar que há onboarding válido disponível.

### RF-14 Consultar o próprio onboarding

**Escopo:** Fora do MVP informado no anexo.

Permitir ao cliente revisar os dados por ele informados.

**Critérios de aceitação**

- [ ] **CA-14.1:** cliente autenticado consulta apenas o próprio onboarding.
- [ ] **CA-14.2:** valores exibidos correspondem ao conteúdo persistido.
- [ ] **CA-14.3:** consulta de outro cliente é bloqueada.

### RF-15 Gerar ficha de treino utilizando IA

**Escopo:** MVP informado no anexo.

Gerar uma orientação/ficha inicial utilizando as informações preenchidas no onboarding.

**Critérios de aceitação**

- [ ] **CA-15.1:** tentativa sem onboarding concluído não gera ficha.
- [ ] **CA-15.2:** com onboarding válido, uma chamada bem-sucedida à IA produz uma ficha estruturada e persistível.
- [ ] **CA-15.3:** a ficha fica associada exclusivamente ao cliente que solicitou/recebeu a geração.
- [ ] **CA-15.4:** a IA irá verificar se os dados de saúde do cliente não são muito graves, caso seja, o plano não é criado pois o treino seria perigoso para o cliente.
- [ ] **CA-15.5:** a ficha será criada baseada nos dados do onboard de cada cliente.

**Nota de consolidação:** Aplicar RN-12 a RN-19 e RN-29 a RN-31. O documento não define o critério de gravidade nem o fluxo completo entre sugestão, revisão e ficha vigente; ver DEC-07.

### RF-16 Visualizar ficha de treino atual

**Escopo:** MVP informado no anexo.

Exibir ao cliente sua ficha vigente em formato utilizável especialmente no celular.

**Critérios de aceitação**

- [ ] **CA-16.1:** cliente com ficha visualiza a versão atual.
- [ ] **CA-16.2:** cliente sem ficha recebe estado vazio apropriado.
- [ ] **CA-16.3:** um cliente não consegue consultar a ficha de outro.

### RF-17 Persistir e versionar a ficha

**Escopo:** MVP informado no anexo.

Manter a ficha gerada e criar nova versão quando alterações dinâmicas forem efetivadas.

**Critérios de aceitação**

- [ ] **CA-17.1:** primeira geração cria a versão inicial.
- [ ] **CA-17.2:** alteração efetivada cria versão posterior e passa a identificá-la como atual.
- [ ] **CA-17.3:** atualizar a página não perde a versão vigente.

**Nota de consolidação:** Versionamento também deve preservar treinos já executados e a identificação do profissional responsável, conforme RN-18 e RN-31.

### RF-18 Conversar com assistente de IA

**Escopo:** MVP informado no anexo.

Disponibilizar chat para o cliente conversar sobre seu treino e fornecer contexto adicional.

**Critérios de aceitação**

- [ ] **CA-18.1:** cliente autenticado envia mensagem e recebe resposta.
- [ ] **CA-18.2:** o assistente recebe contexto da ficha vigente e, quando necessário, do onboarding daquele cliente.
- [ ] **CA-18.3:** mensagens de um cliente não aparecem na conversa de outro.
- [ ] **CA-18.4:** indisponibilidade do provedor retorna erro controlado e não corrompe o treino.

### RF-19 Alterar dinamicamente o treino via IA

**Escopo:** MVP informado no anexo.

Adaptar a ficha quando o cliente relatar pelo chat que dor, limitação ou problema anterior está interferindo no treino.

**Critérios de aceitação**

- [ ] **CA-19.1:** em cenário de teste no qual o cliente relata que um problema interfere em determinado exercício, a IA produz uma adaptação relacionada ao contexto.
- [ ] **CA-19.2:** a mudança aprovada pelo fluxo resulta em nova versão atual.
- [ ] **CA-19.3:** partes não relacionadas não são apagadas indevidamente.
- [ ] **CA-19.4:** a ficha alterada permanece após nova autenticação.

**Nota de consolidação:** O texto exige mudança aprovada, mas não detalha quem aprova nem os estados da proposta. Definir esse fluxo em DEC-07; preservar a ficha aprovada conforme RN-16 e RN-17.

### RF-20 Receber evento de uso da catraca externo

**Escopo:** Fora do MVP informado no anexo.

Disponibilizar endpoint REST para que o serviço externo informe o resultado de uma identificação facial.

**Critérios de aceitação**

- [ ] **CA-20.1:** requisição autenticada e válida é aceita conforme o JSON documentado.
- [ ] **CA-20.2:** JSON malformado retorna erro de validação.
- [ ] **CA-20.3:** integração não exige que a aplicação implemente algoritmo de funcionamento da catraca.
- [ ] **CA-20.4:** evento duplicado com mesmo identificador não cria registros duplicados.

**Nota de consolidação:** O resultado facial vem de um serviço externo. O contrato JSON, a autenticação da integração e a relação com a decisão de liberar a catraca ainda precisam ser definidos; ver DEC-11.

### RF-21 Verificar identidade e habilitação do usuário para acesso

**Escopo:** Fora do MVP informado no anexo.

Associar a identidade informada pelo serviço facial ao cliente e verificar se a conta está habilitada.

**Critérios de aceitação**

- [ ] **CA-21.1:** identidade externa conhecida é associada ao cliente correspondente.
- [ ] **CA-21.2:** identidade desconhecida gera decisão de negação/identidade desconhecida.
- [ ] **CA-21.3:** cliente explicitamente desativado não é retornado como habilitado.
- [ ] **CA-21.4:** resposta de reconhecimento deve ter uma precisão aceitável de no mínimo 95% para ser aceito

**Nota de consolidação:** O valor mínimo de 95% foi preservado. “Precisão” pode se referir à qualidade do modelo ou à confiança de uma correspondência; a métrica e seu uso precisam ser esclarecidos em DEC-09. Identificação não substitui autorização de entrada: aplicar RN-06, RN-35 e RN-36.

### RF-22 Inserção dos dados iniciais de biometria de cada cliente.

**Escopo:** Fora do MVP informado no anexo.

Um atendente poderá cadastrar uma foto de rosto válida para o cliente, os dados dessa foto serão usados para a biometria da entrada.

**Critérios de aceitação**

- [ ] **CA-22.1:** A foto deve passar um limiar de precisão previamente escolhido.
- [ ] **CA-22.2:** Caso outra foto seja cadastrada, ela deverá substituir a antiga que já estava cadastrada, a antiga então será descartada.
- [ ] **CA-22.3:** Apenas funcionários devem ter o poder de mudar os dados da foto de biometria associada a cada cliente.

**Nota de consolidação:** O descarte da foto anterior precisa coexistir com a rastreabilidade das alterações críticas prevista em RN-26 e RN-27. Definir permissões, limiar da foto e política de retenção em DEC-04, DEC-09 e DEC-18.

### RF-23 Registrar entrada, saída e frequência

**Escopo:** Fora do MVP informado no anexo.

Persistir eventos de acesso usados como histórico/frequência.

**Critérios de aceitação**

- [ ] **CA-23.1:** evento de entrada válido cria registro de entrada.
- [ ] **CA-23.2:** evento de saída válido cria registro de saída.
- [ ] **CA-23.3:** evento repetido não conta duas vezes.
- [ ] **CA-23.4:** os registros possuem data/hora e cliente relacionados.

### RF-24X Calcular lotação atual

**Escopo:** Fora do MVP informado no anexo.

Derivar a quantidade de pessoas atualmente presentes a partir dos eventos de entrada e saída.

**Critérios de aceitação**

- [ ] **CA-24.1:** uma entrada válida incrementa a lotação uma vez.
- [ ] **CA-24.2:** uma saída válida decrementa a lotação uma vez.
- [ ] **CA-24.3:** processamento duplicado do mesmo evento não altera novamente o total.
- [ ] **CA-24.4:** o valor não é exibido como negativo.

**Nota de consolidação:** O sufixo X foi mantido, pois seu significado não é explicado. RN-37 descreve contagem por câmeras em espaços da academia, enquanto este RF calcula presença por entradas e saídas. Resolver DEC-02 e DEC-10 antes de escolher o comportamento.

### RF-25X Exibir lotação atual

**Escopo:** Fora do MVP informado no anexo.

Mostrar ao cliente a quantidade de pessoas treinando no momento.

**Critérios de aceitação**

- [ ] **CA-25.1:** página exibe o valor calculado por RF-24 para usuários.
- [ ] **CA-25.2:** após novo evento processado, uma nova consulta reflete o novo total.
- [ ] **CA-25.3:** informação é legível em viewport de celular.

**Nota de consolidação:** O anexo referencia RF-24 neste critério, mas identifica a linha correspondente como RF-24X. Essa referência foi preservada e aponta para o item anterior. Ver DEC-02 e DEC-10.

### RF-26 Registrar e atualizar situação de cobrança

**Escopo:** Fora do MVP informado no anexo.

Manter o controle básico de mensalidades/cobranças de cada cliente.

**Critérios de aceitação**

- [ ] **CA-26.1:** usuário autorizado registra competência/período, vencimento e situação.
- [ ] **CA-26.2:** atualização persiste.
- [ ] **CA-26.3:** registro fica associado ao cliente correto.

### RF-27 Consultar situação de cobrança

**Escopo:** Fora do MVP informado no anexo.

Permitir a consulta da situação financeira básica já registrada.

**Critérios de aceitação**

- [ ] **CA-27.1:** usuário autorizado consulta os registros do cliente.
- [ ] **CA-27.2:** o cliente pode visualizar a própria situação quando essa tela fizer parte da interface.
- [ ] **CA-27.3:** cliente não consulta mensalidade de terceiros.

### RF-28 Disponibilizar dashboard administrativo

**Escopo:** Fora do MVP informado no anexo.

Apresentar uma página inicial administrativa consolidando informações do sistema.

**Critérios de aceitação**

- [ ] **CA-28.1:** somente perfil autorizado acessa o dashboard.
- [ ] **CA-28.2:** página carrega dados provenientes dos módulos existentes, como a fatura mensal, anual e total; número de clientes assinantes e funcionários; histórico de acesso dos clientes dividido por dias/horas e possíveis outros.
- [ ] **CA-28.3:** falha de um indicador não concede acesso indevido nem exibe dados de outro contexto.

**Nota de consolidação:** Os indicadores financeiros dependem de definir o significado de fatura, faturamento e lucro; ver DEC-13.

### RF-29 Exibir indicadores consolidados no dashboard

**Escopo:** Fora do MVP informado no anexo.

Tornar o dashboard útil apresentando indicadores oriundos das funções já solicitadas.

**Critérios de aceitação**

- [ ] **CA-29.1:** exibe ao menos quantidade de clientes ativos, histórico de frequência nas semanas e lotação atual.
- [ ] **CA-29.2:** quando os módulos correspondentes estiverem implementados, pode exibir resumo de lucro total e por mês.

**Nota de consolidação:** O indicador de lotação depende de DEC-10. Lucro depende de uma definição de cálculo e de dados ainda não especificados, conforme DEC-13.

### RF-30 Gerenciar agenda de aulas de ginástica

**Escopo:** Fora do MVP informado no anexo.

Permitir que um usuário administrativo registre os dias e horários que serão posteriormente exibidos.

**Critérios de aceitação**

- [ ] **CA-30.1:** administrador cria aula com informações mínimas de identificação, data e horário.
- [ ] **CA-30.2:** consegue alterar ou retirar uma ocorrência da agenda.
- [ ] **CA-30.3:** alterações aparecem na visualização pública/autenticada correspondente.

**Nota de consolidação:** A regra de capacidade RN-25 é condicional. Recorrência, visibilidade da agenda e eventual fluxo de reservas precisam ser definidos em DEC-14.

### RF-31 Disponibilizar a compra de planos de academia

**Escopo:** Fora do MVP informado no anexo.

Permitir que um usuário compre um plano de academia que estará linkado a sua conta. Esse plano terá uma validade na data X, e deverá ser expirado quando passar pelo tempo de expiração necessitando de um novo pagamento para ser validado.

**Critérios de aceitação**

- [ ] **CA-31.1:** Status do cliente de habilitado só deve mudar se o pagamento foi aceito com confirmação da API.

**Nota de consolidação:** A confirmação do pagamento deve ser relacionada às demais condições de habilitação e entrada, sem apagar essas condições. Ver DEC-05 e DEC-12, além de RN-22, RN-24, RN-35 e RN-36.

### RF-32 Gerenciar equipamentos da academia

**Escopo:** Fora do MVP informado no anexo.

Permitir que usuário administrativo cadastre, consulte, atualize e desative os equipamentos disponibilizados pela academia, incluindo suas informações básicas e imagem de apresentação.

**Critérios de aceitação**

- [ ] **CA-32.1:** usuário administrativo autorizado consegue cadastrar equipamento informando, no mínimo, nome e situação;
- [ ] **CA-32.2:** o sistema permite associar uma imagem ao equipamento;
- [ ] **CA-32.3:** equipamento cadastrado permanece disponível após nova consulta;
- [ ] **CA-32.4:** usuário autorizado consegue alterar as informações do equipamento;
- [ ] **CA-32.5:** O equipamento desativado deixa de aparecer como equipamento disponível ao cliente, sem necessidade de excluir seu registro.

### RF-33 Consultar equipamentos disponíveis

**Escopo:** Fora do MVP informado no anexo.

Permitir que visitantes ou clientes visualizem os equipamentos disponibilizados pela academia, juntamente com suas informações básicas e respectivas imagens.

**Critérios de aceitação**

- [ ] **CA-33.1:** a interface apresenta a relação dos equipamentos ativos cadastrados;
- [ ] **CA-33.2:** cada equipamento apresenta pelo menos nome e imagem, quando houver imagem cadastrada;
- [ ] **CA-33.3:** o usuário consegue consultar informações adicionais do equipamento, quando cadastradas;
- [ ] **CA-33.4:** equipamentos desativados não aparecem como disponíveis;
- [ ] **CA-33.5:** a listagem permanece utilizável em dispositivos móveis.

### 3.1 Approved product-extension requirements

These requirements originate in `docs/product-extensions.md`, not the original
source. That file remains authoritative for full dependency, privacy, and
unresolved-decision detail.

#### EXT-RF-AI-01 — Conversational AI onboarding

**Scope:** approved MVP product extension. **Related originals:** RF-10–RF-13,
RF-15, RF-18, RN-05, RN-11, RN-23, RN-29, RN-30.

An authenticated client may start or resume a progressive AI conversation that
maps recognized answers into their authoritative structured onboarding. The AI
must leave missing/invalid information incomplete, must not diagnose, must not
bypass validation, and must preserve the secure-link/form route.

Questions may cover objectives, approved physical information, prior experience
where applicable, limitations/complaints, medications, health conditions, and
other fields only when they exist in the approved onboarding schema.

Acceptance: `EXT-CA-AI-01.1` own-client start/resume;
`EXT-CA-AI-01.2` progressive schema-based mapping and persistence;
`EXT-CA-AI-01.3` no invented values or validation bypass;
`EXT-CA-AI-01.4` resumable state; `EXT-CA-AI-01.5` RF-13 completion gates RF-15;
`EXT-CA-AI-01.6` cross-client isolation; `EXT-CA-AI-01.7` no diagnosis and
controlled provider failure; `EXT-CA-AI-01.8` coexistence with link/form.

#### EXT-RF-SOC-01 — Controlled progress sharing

**Scope:** approved post-MVP extension. **Related originals:** RF-04, RF-05,
RN-04, RN-05, RN-11, RN-23, RN-28, RN-33.

An authenticated client owns each progress update and selects private or shared
visibility. Only explicitly permitted users may view it; only its author may
modify/delete it. Sensitive account, health, biometric, financial,
authentication, administrative, or presence data is never inserted
automatically.

Acceptance: `EXT-CA-SOC-01.1` authenticated ownership;
`EXT-CA-SOC-01.2` private/shared control; `EXT-CA-SOC-01.3` enforced visibility;
`EXT-CA-SOC-01.4` author-only mutation/deletion; `EXT-CA-SOC-01.5` no automatic
sensitive content; `EXT-CA-SOC-01.6` no unapproved social-network features.

#### EXT-RF-EQP-01 — Equipment quantity by logical type/model

**Scope:** approved post-MVP extension. **Related originals:** RF-32, RF-33,
RN-04, RN-33.

Administrative equipment management and client/visitor consultation must
support the total count of active units for an approved logical type/model,
alongside name, optional image, and additional RF-33 information.

Acceptance: `EXT-CA-EQP-01.1` authorized grouping management;
`EXT-CA-EQP-01.2` active total displayed; `EXT-CA-EQP-01.3` deactivation updates
the count while preserving required history; `EXT-CA-EQP-01.4` total units are
never represented as real-time free/available units.

#### EXT-RF-PRES-01 — Opt-in visible presence

**Scope:** approved post-MVP extension, blocked by `EXT-DEC-PRES-01` and DEC-10.
**Related originals:** RF-23–RF-25X, RN-04, RN-05, RN-10, RN-11, RN-23, RN-34,
RN-37.

Named presence is a separate opt-in client feature, not anonymous occupancy and
not inferred from camera/biometric data. A non-opted-in client never appears by
name to another client, and the view exposes only minimal approved profile data.

Acceptance: `EXT-CA-PRES-01.1` default-off opt-in;
`EXT-CA-PRES-01.2` non-consenting clients excluded; `EXT-CA-PRES-01.3` preference
lifecycle enforced; `EXT-CA-PRES-01.4` sensitive data excluded;
`EXT-CA-PRES-01.5` anonymous count remains independent;
`EXT-CA-PRES-01.6` staff visibility does not imply client/public visibility.

No extension approves followers, friends, messages, comments, likes, rankings,
leaderboards, or live equipment-use tracking.

### 3.2 Client-facing training and assistant interpretation (DEC-19)

RF-16 is implemented as a personal, mobile-usable area where the authenticated
client views only their current training-plan version, its exercises, and the
relevant instructions contained in that approved version. A browser-supplied
client ID cannot select the plan.

RF-18/RF-19 remain client-facing after onboarding. When functionally necessary
and authorized, the assistant may receive only that authenticated client's
structured onboarding, current approved plan, permitted version/history
context, and client-visible exercise/equipment information already implemented
by an approved module. Missing modules do not authorize invented context.
Suggestions and chat responses do not become the current plan: approval,
versioning, safety, professional responsibility, manual fallback, and history
rules in RF-17/RF-19 and RN-12–RN-19/RN-31 continue to govern changes.

## 4 Requisitos não funcionais

Os seis RNF abaixo preservam todos os critérios do anexo. Parâmetros de medição que não foram definidos estão reunidos em DEC-16.

### RNF01 Desempenho

O sistema deve apresentar respostas rápidas às operações realizadas pelos usuários.

**Critérios de aceitação**

- [ ] **CA-RNF01.1:** operações comuns de consulta, navegação e gravação devem apresentar resposta ao usuário em até 2 segundos em condições normais de uso.
- [ ] **CA-RNF01.2:** operações que dependam de serviços externos ou processamento naturalmente mais demorado devem apresentar indicação de processamento, sem aparentar travamento da interface.
- [ ] **CA-RNF01.3:** em caso de indisponibilidade ou demora de um serviço externo, o sistema deve retornar uma mensagem de erro controlada, sem bloquear indefinidamente a operação.

### RNF02 Usabilidade

O sistema deve possuir uma interface limpa, intuitiva e simples de utilizar, com baixa necessidade de treinamento.

**Critérios de aceitação**

- [ ] **CA-RNF02.1:** as funcionalidades previstas para cada perfil devem ser acessíveis por meio de navegação e rótulos compreensíveis, sem exigir conhecimento técnico do sistema.
- [ ] **CA-RNF02.2:** formulários devem indicar claramente campos obrigatórios, erros de preenchimento e ações disponíveis.
- [ ] **CA-RNF02.3:** um usuário representativo deve conseguir executar as principais tarefas do seu perfil sem necessidade de treinamento específico além de uma orientação inicial.

### RNF03 Responsividade

A interface deverá adaptar-se a smartphones, tablets e computadores, priorizando uma boa experiência de uso em dispositivos móveis.

**Critérios de aceitação**

- [ ] **CA-RNF03.1:** as telas principais devem permanecer utilizáveis em smartphones, tablets e computadores, sem sobreposição ou corte de conteúdo.
- [ ] **CA-RNF03.2:** menus, botões, formulários e elementos de interação devem permanecer acessíveis e utilizáveis em telas pequenas.
- [ ] **CA-RNF03.3:** o conteúdo principal não deve exigir rolagem horizontal em smartphones nas resoluções suportadas pelo projeto.

### RNF04 Manutenibilidade

O sistema deverá ser desenvolvido de maneira a possuir baixa necessidade de manutenção, favorecendo organização do código, modularidade, facilidade de evolução e facilidade de correção de problemas.

**Critérios de aceitação**

- [ ] **CA-RNF04.1:** alterações em um módulo não devem exigir modificações generalizadas em outros módulos quando não houver dependência funcional necessária.
- [ ] **CA-RNF04.2:** os componentes do sistema devem possuir responsabilidades bem definidas, evitando lógica duplicada e acoplamento desnecessário.
- [ ] **CA-RNF04.3:** alterações relevantes devem possuir testes relacionados suficientes para detectar regressões nas funcionalidades afetadas.

### RNF05 Disponibilidade

O sistema deverá estar disponível para utilização pelos usuários 24 horas por dia.

**Critérios de aceitação**

- [ ] **CA-RNF05.1:** os serviços principais devem permanecer disponíveis continuamente, exceto durante manutenções programadas.
- [ ] **CA-RNF05.2:** falhas de um serviço externo, como provedor de IA ou e-mail, não devem indisponibilizar funcionalidades internas que não dependam diretamente desse serviço.
- [ ] **CA-RNF05.3:** durante indisponibilidade de um componente externo, o sistema deve informar a falha de forma controlada e permitir a continuidade das operações independentes.

### RNF06 Integração

As integrações com sistemas externos deverão ser realizadas de forma desacoplada, permitindo que serviços externos possam ser substituídos ou atualizados sem exigir alterações generalizadas no sistema.

**Critérios de aceitação**

- [ ] **CA-RNF06.1:** a comunicação com cada serviço externo deve ocorrer por meio de uma interface ou camada de integração definida, evitando dependência direta espalhada pelo domínio da aplicação.
- [ ] **CA-RNF06.2:** a substituição de um provedor externo compatível deve exigir alterações concentradas na respectiva camada de integração, sem modificar generalizadamente as regras de negócio.
- [ ] **CA-RNF06.3:** falhas ou mudanças de contrato de um serviço externo devem ser tratadas pela camada de integração e não devem expor detalhes internos do provedor às demais camadas.

### 4.1 Restrições transversais presentes em outras seções

O anexo também registra restrições de qualidade e segurança dentro de regras de negócio e critérios funcionais. Elas continuam aplicáveis com seus IDs originais; esta tabela apenas facilita sua localização.

| Tema | Referências e condição a observar |
| --- | --- |
| Autenticação e autorização | RF-04, RF-05 e RN-02 a RN-05: controlar sessão, perfil e acesso também na API. |
| Privacidade e segregação | RF-12, RF-18, RN-10, RN-11, RN-23, RN-28, RN-29 e RN-34: limitar acesso e exposição de dados de saúde, biometria, logs, exportações e contexto da IA. |
| Integridade e histórico | RF-17, RF-20, RF-23, RF-24X, RN-01, RN-18, RN-20 e RN-33: manter identidade, histórico, relacionamentos e tratamento de duplicidade. |
| Auditoria e rastreabilidade | RN-03, RN-09, RN-21, RN-26, RN-27, RN-31 e RN-32: registrar responsáveis, motivos, avisos e datas de forma consistente. |
| Continuidade com falhas externas | RN-08, RN-19, RNF01, RNF05 e RNF06: prever alternativa para reconhecimento facial, treino manual e tratamento controlado de falhas. |
| Qualidade biométrica | CA-21.4, CA-22.1 e RN-07: observar o mínimo de 95% citado e o limiar da foto, com métricas a esclarecer em DEC-09. |
| Implantação | CA-06.4 e seção 6: contemplar isolamento do SMTP em contêiner, Docker Compose e a indicação de firewall. |

## 5 Regras de negócio

Todas as 37 regras do anexo estão preservadas abaixo, inclusive aquelas que também descrevem funções ou restrições não funcionais. Regras condicionais mantêm suas condições de aplicação.

| ID | Regra de negócio | Aplicação indicada |
| --- | --- | --- |
| RN-01 | Cada pessoa deve possuir identidade única no sistema segundo o identificador definido pelo projeto. | Cadastro |
| RN-02 | Usuário inativo não poderá autenticar-se normalmente. | Autenticação |
| RN-03 | Funcionário inativado perde as permissões operacionais, mas seu histórico permanece associado a ele. | Funcionários/Auditoria |
| RN-04 | Toda operação protegida deve considerar o perfil/permissão do usuário autenticado. | Segurança |
| RN-05 | Um cliente somente pode visualizar dados pertencentes ao próprio contexto, salvo funções especificamente compartilhadas. | Privacidade |
| RN-06 | Reconhecimento facial identifica/verifica a pessoa; a autorização de entrada deve ocorrer em etapa separada. | Biometria/Acesso |
| RN-07 | Correspondência facial abaixo do limiar configurado nunca deve ser convertida automaticamente em identificação positiva. | Biometria |
| RN-08 | Deve existir fluxo alternativo para falha de reconhecimento facial. | Biometria |
| RN-09 | Toda liberação manual que contorne uma regra normal de acesso deve registrar responsável e motivo. | Controle de acesso |
| RN-10 | Dados biométricos devem ser tratados separadamente dos dados cadastrais comuns. | LGPD |
| RN-11 | Informações médicas, lesões ou restrições registradas não devem ficar disponíveis a funcionários sem necessidade funcional. | LGPD |
| RN-12 | Sugestões geradas pela IA poderão ser vistas pelos funcionários instrutores para avaliar sua validade. | IA |
| RN-13 | A IA não deve criar sugestões de treino para clientes com casos graves de saúde (como problemas cardíacos graves) | IA/Treino |
| RN-14 | O professor deve conseguir modificar integralmente uma sugestão. | IA/Treino |
| RN-15 | Restrições do cliente possuem precedência sobre otimizações sugeridas pela IA. | IA/Treino |
| RN-16 | A IA não deve modificar silenciosamente uma ficha já aprovada. | IA/Treino |
| RN-17 | Alteração proposta pela IA em ficha existente deve resultar em nova proposta/versão. | IA/Treino |
| RN-18 | Treinos antigos executados não podem ser modificados retroativamente ao atualizar a ficha atual. | Histórico |
| RN-19 | A falha do serviço de IA não poderá impedir o instrutor de montar treino manualmente. | Disponibilidade funcional |
| RN-20 | Um exercício inativo pode permanecer em fichas históricas, mas não deve ser selecionável normalmente em novas prescrições. | Exercícios |
| RN-21 | Avaliações devem possuir data e responsável para permitir evolução cronológica. | Avaliação |
| RN-22 | Apenas planos ativos podem originar novas matrículas. | Planos |
| RN-23 | Informações sensíveis não devem aparecer desnecessariamente em logs técnicos. | LGPD |
| RN-24 | Se a academia bloquear inadimplentes, o bloqueio deverá ser aplicado pelo motor de regras de acesso, não pelo reconhecimento facial. | Financeiro/Acesso |
| RN-25 | Se forem oferecidas aulas com limite de participantes, reservas confirmadas não podem exceder capacidade sem ação excepcional autorizada. | Agenda |
| RN-26 | Alterações críticas de permissão, biometria e configuração devem gerar aviso. | Aviso |
| RN-27 | O usuário que executar uma ação problemática não deve poder apagar livremente a evidência da própria ação. | Auditoria |
| RN-28 | Exportações devem respeitar as mesmas permissões existentes nas telas/APIs. | Segurança |
| RN-29 | Dados de um cliente jamais devem compor contexto de IA destinado a outro cliente. | IA/Privacidade |
| RN-30 | Respostas da IA não devem ser apresentadas como diagnóstico médico. | IA |
| RN-31 | O professor/profissional deve permanecer identificável como responsável pelas fichas que ele alterou/criou. | Treino |
| RN-32 | Todo registro temporal deve utilizar padrão consistente de data/hora para preservar a rastreabilidade. | Sistema |
| RN-33 | Exclusão/inativação de entidade não deve quebrar relacionamentos históricos necessários para auditoria. | Integridade |
| RN-34 | Dados biométricos não devem ser enviados para relatórios operacionais comuns. | LGPD |
| RN-35 | Caso o aluno não possua uma matrícula válida, o sistema deverá impedir seu acesso. São consideradas situações inválidas: matrícula inexistente ou matrícula vencida. | Controle de acesso |
| RN-36 | A liberação da catraca somente deverá ocorrer após o sistema validar identidade do aluno, existência da matrícula, validade da matrícula, modalidade contratada e quantidade de acessos permitida. | Autorização de entrada |
| RN-37 | O sistema de lotação da academia deve apresentar, de forma auxiliar, a quantidade de pessoas que estão em certos espaços da academia, através da contagem de pessoas com uso de modelo de visão computacional vinculado às câmeras de vigilância. | Lotação de academia |

**Nota de classificação:** RN-37 descreve uma funcionalidade de contagem e apresentação de lotação por visão computacional. RN-08, RN-09, RN-12, RN-14, RN-19, RN-21 e RN-26 também implicam fluxos que precisam ser detalhados. Sua numeração original foi mantida; ver DEC-10, DEC-11 e DEC-15.

## 6 Tecnologias e restrições técnicas

### 6.1 Historical technology entries from the source

The following TEC entries are preserved for traceability only. Where they list
alternatives, DEC-03's approved baseline below—not the historical alternative—is
the active implementation architecture.

| ID | Camada | Tecnologia indicada | Motivo registrado no anexo |
| --- | --- | --- | --- |
| TEC-01 | Frontend | React + TypeScript | Componentização, forte ecossistema e boa adequação para interface SPA responsiva |
| TEC-02 | Build frontend | Vite | Setup simples para projeto React/TypeScript e build de produção |
| TEC-03 | Backend | NestJS + Python | Arquitetura modular, controllers/services/guards e bom suporte a REST/OpenAPI; Adicionar Firewall; Adicionar docker |
| TEC-04 | Banco | PostgreSQL | Dados do domínio são fortemente relacionais e necessitam constraints/transações |
| TEC-05 | Auth | Keycloak/OIDC, ou autenticação segura integrada ao backend em escopo reduzido | Evita reinventar vários mecanismos de identidade e permite papéis padronizados |
| TEC-06 | API | REST + JSON + OpenAPI | Adequado à interface web e à integração externa de reconhecimento |
| TEC-07 | IA | Adaptador para provedor de LLM | Evita acoplamento do domínio a um único fornecedor |
| TEC-08 | Infra | Docker Compose | Facilita reproduzir frontend/backend/banco/identidade localmente e em qualquer outra máquina |
| TEC-09 | E-mail | SMTP ou API de provedor de e-mail | Necessário ao convite e recuperação |
| TEC-10 | Testes | Unitários + integração + contrato da API | Particularmente importante para IA e integração facial |

### 6.1.1 Approved current technology baseline (DEC-03)

| Area | Approved implementation choice |
| --- | --- |
| Architecture/backend | Python 3.13.15 modular monolith; FastAPI 0.141.1. NestJS has no MVP responsibility and requires a future explicit decision. |
| Persistence | PostgreSQL; SQLAlchemy 2.x synchronous access; Alembic migrations; psycopg 3. |
| Frontend | React 19.3.0, TypeScript 5.9.3, Vite 8.3.0, MUI 9.0.0; Node.js 24.21.0 LTS. |
| Authentication | Keycloak 26.6.3 through OIDC; identity model in section 2.2. |
| API | REST + JSON + OpenAPI. |
| E-mail | SMTP adapter; Mailpit 1.30.7 in local Docker development. |
| AI | Provider-independent adapter; provider/model and contract remain DEC-08. |
| Runtime/deployment | Docker Compose on a Linux host; host-level UFW; PostgreSQL and other internal services are not directly Internet-exposed. |
| Tests | pytest/FastAPI `TestClient`; Vitest + React Testing Library. No Jest/Supertest for the Python backend. |
| Hosting | Undecided. |

Exact pinned versions and amendment history remain authoritative in DEC-03;
this document does not authorize upgrades.

### 6.2 Restrições técnicas que também devem orientar o trabalho

- **SMTP isolado:** CA-06.4 exige que o servidor SMTP seja isolado em um contêiner Docker. Essa exigência deve ser compatibilizada com a alternativa de API de e-mail indicada em TEC-09.
- **Backend:** TEC-03 cita NestJS e Python conjuntamente. A responsabilidade de cada um não está definida; não interpretar a indicação como uma escolha automática entre as duas tecnologias.
- **Firewall:** a linha do backend pede a adição de firewall, mas não especifica produto, local de execução, portas ou regras.
- **Contêineres e execução:** TEC-03 menciona Docker e TEC-08 indica Docker Compose para reproduzir frontend, backend, banco e identidade em outras máquinas.
- **Autenticação:** TEC-05 oferece Keycloak/OIDC ou autenticação segura integrada ao backend em escopo reduzido. Escolher e registrar uma abordagem antes de consolidar a implementação de identidade.
- **Contratos de API:** TEC-06 indica REST, JSON e OpenAPI. RF-20 exige contrato JSON documentado, autenticação da integração, validação e tratamento de eventos duplicados.
- **IA desacoplada:** TEC-07 e RNF06 exigem uma camada de integração que evite prender o domínio a um único provedor de LLM. O fornecedor e o modelo não estão definidos.
- **Serviço facial externo:** RF-20 pressupõe uma integração externa de identificação. O funcionamento da catraca não precisa ser implementado pela aplicação, conforme CA-20.3; as regras de autorização continuam pertencendo ao sistema.
- **Contagem por câmeras:** RN-37 menciona um modelo de visão computacional ligado às câmeras de vigilância. Não informa modelo, biblioteca, protocolo das câmeras nem associação desse processamento ao Python.
- **Pagamentos:** RF-31 exige confirmação por API, mas não escolhe gateway ou provedor de pagamento.
- **Testes:** TEC-10 prevê testes unitários, de integração e de contrato da API, com atenção às integrações de IA e reconhecimento facial.

Choices still unspecified must be handled under DEC-08–DEC-16 and extension
decision gates. Do not add providers or infrastructure as if they were approved.

## 7 Referências de domínio e arquitetura

### 7.1 Modelo de dados apresentado nos diagramas

O anexo contém diferentes representações do modelo de dados. Elas servem de referência para o domínio, mas não constituem um esquema único e completamente conciliado.

| Área | Entidades e conceitos representados |
| --- | --- |
| Identidade e administração | Usuário, cliente, funcionário, administrador, perfil, permissão, sessão, recuperação, configuração e auditoria. |
| Academia e oferta | Academia, plano, assinatura ou matrícula, cobrança, pagamento, aula de ginástica e equipamento. |
| Onboarding e saúde | Onboarding, dados físicos, queixas, medicações, condições de saúde e avaliações. |
| Treinos | Ficha de treino, versão da ficha, item da ficha, exercício e treino executado. |
| IA | Interações, conversa, mensagens e propostas de alteração de treino. |
| Acesso físico | Biometria, identificação facial, catraca, decisão de acesso, liberação manual, registros de entrada e saída e frequência. |

Referências conceituais recorrentes incluem o vínculo do cliente ao onboarding e à ficha, o versionamento da ficha, a associação de itens a exercícios, o vínculo de contratação com plano e cliente e a associação dos registros de acesso ao cliente.

Os diagramas variam em nomenclatura e detalhamento, incluindo assinatura versus matrícula e a associação de interações de IA a itens ou versões. Antes de criar migrações, conciliar esses pontos com os RF e RN da tarefa; ver DEC-17. A existência de uma entidade no diagrama não define, por si só, um novo fluxo completo de interface ou CRUD.

### 7.1.1 Implementation-oriented domain model

This is a domain inventory, not a final SQL schema. Unapproved fields and
cardinalities remain undecided.

| Entity/concept | Purpose, ownership, relationships, privacy/lifecycle |
| --- | --- |
| Account | Local identity linkage. Application UUID; unique normalized e-mail; unique nullable Keycloak subject; active state. Owns no password. Reusable by client/employee/admin identities. |
| Client | Client-domain profile with independent UUID and unique Account FK. Owns onboarding, plans, progress, and attendance relationships; deactivation preserves history. |
| Employee/role authorization | Later employee profile linked to Account; Keycloak roles and backend policy enforce specialization. Exact employee schema awaits RF-07/RF-08 work. |
| Onboarding / structured data | Client-owned draft/completed aggregate for approved physical and health fields. Structured values are authoritative; completion/timestamps follow RF-13. Health access is need-to-know. |
| AI onboarding conversation/message | Client-owned resumable EXT-RF-AI-01 interaction that maps into structured onboarding. Retention and exact message schema await DEC-08/DEC-18. |
| TrainingPlan / TrainingPlanVersion / TrainingPlanItem | Client-owned plan aggregate, immutable/versioned current/history states, responsible professional, structured exercise items. Approval states await DEC-07/DEC-15. |
| Exercise | Referenced prescription content; inactive exercises remain in history under RN-20. Full management flow awaits DEC-15. |
| AI training conversation/message/proposal | Client-scoped RF-18/RF-19 context and proposed changes. A proposal is not a current approved plan; changes use the version lifecycle. |
| Equipment / logical type-model | RF-32 administrative records and RF-33 catalog. EXT-RF-EQP-01 grouping/count model awaits EXT-DEC-EQP-01; count is not live availability. |
| ProgressUpdate | Client-author-owned social item with private/shared visibility. Audience, retention, and deletion details await EXT-DEC-SOC-01. No sensitive data is automatically derived into it. |
| Plan/Enrollment/Subscription | Client contracting and validity concepts for RF-31/RN-22/RN-35/RN-36. Cardinality, modalities, and validity await DEC-12. |
| Charge/Payment | Client financial records and external confirmation. Provider/model and financial meanings await DEC-12/DEC-13; access is restricted. |
| Biometric data | Separately protected RF-22 data; not ordinary profile data. Quality, replacement, retention, and audit await DEC-09/DEC-18. |
| AccessEvent / attendance | Idempotent client-associated entry/exit records with timestamps under RF-20/RF-23. Integration contract and exceptions await DEC-11. |
| Occupancy records | Anonymous derived/event and possible auxiliary camera counts. Source-of-truth/display behavior awaits DEC-10. |
| Presence preference/view | EXT-RF-PRES-01 opt-in state and derived named presence. Persistence and consent lifecycle await EXT-DEC-PRES-01. |
| Class/schedule | RF-30 class occurrences; recurrence, capacity, visibility, and reservations await DEC-14. |

Ownership rules apply at the backend: authenticated clients receive only their
own protected aggregates unless an explicit shared-visibility requirement says
otherwise.

### 7.2 Limites de arquitetura

A fonte menciona diagramas de MER e microsserviços e indica arquitetura modular no backend. As imagens incorporadas concentram-se em entidades e relacionamentos; não estabelecem uma divisão inequívoca dos serviços, seus contratos ou sua implantação.

Portanto, a fronteira entre módulos e processos, a distribuição de responsabilidades entre NestJS e Python, a autenticação escolhida e o desenho de implantação precisam ser registrados em DEC-03. O requisito de desacoplamento das integrações permanece válido em qualquer solução adotada.

DEC-03 has since selected the current boundary in section 6.1.1; the paragraph
above remains historical source context, not an active alternative.

### 7.3 Cross-cutting authenticated API rules

- For a client-owned protected resource, the backend derives the account and
  client from the verified Keycloak subject whenever possible.
- A `client_id` in a path, query, body, local storage, or frontend state is never
  proof that the caller owns that client.
- A client accesses only their protected data unless an explicit requirement
  defines shared visibility, such as EXT-RF-SOC-01 or EXT-RF-PRES-01.
- Administrative and professional APIs enforce role and functional-need policy
  independently of frontend routes, menus, or hidden controls.
- Direct API calls receive the same denial as the UI; obscuring controls is not
  authorization.
- External adapters receive only the minimum permitted client context and map
  provider failures to controlled application errors.

## 8 MVP e sequência de implementação

### 8.1 MVP explicitamente informado

O anexo inclui os seguintes 15 requisitos no MVP:

`RF-01`, `RF-02`, `RF-03`, `RF-04`, `RF-05`, `RF-09`, `RF-10`, `RF-11`, `RF-12`, `RF-13`, `RF-15`, `RF-16`, `RF-17`, `RF-18` e `RF-19`.

O caminho crítico informado é:

Cadastro → Acesso → E-mail → Onboarding → Geração por IA → Ficha → Chat → Adaptação dinâmica.

Essa lista não dispensa os RNF e RN associados aos requisitos escolhidos.

DEC-19 adds `EXT-RF-AI-01` to the planned MVP onboarding experience without
claiming that it existed in the original MVP list. `EXT-RF-SOC-01`,
`EXT-RF-EQP-01`, and `EXT-RF-PRES-01` are approved post-MVP extensions.

### 8.2 Dependências que precisam ser conciliadas

| Dependência | Implicação para o MVP |
| --- | --- |
| RF-03 exige foto válida para clientes habilitados, enquanto RF-22 não integra o MVP. | Definir como ocorre a habilitação inicial e em que etapa a biometria será necessária; DEC-05. |
| RF-09 exige infraestrutura de e-mail. | Definir envio e tratamento de falha antes de validar os convites, mesmo que recuperação de acesso por RF-06 fique para outra entrega. |
| RF-15 e RF-19 dependem de contexto de saúde e aprovação de alterações. | Definir bloqueios, revisão e versionamento junto de RN-12 a RN-19; DEC-07. |
| RN-14 e RN-19 exigem edição integral pelo professor e montagem manual de treino. | Detalhar como esses fluxos se encaixam na entrega que usar IA; não considerá-los implementados apenas porque RF-15 está pronto. |
| RF-04 e RF-05 pressupõem usuários e permissões disponíveis. | Definir o provisionamento inicial e a matriz de permissões; DEC-04. |

The reproducible dependency path now is:

`client provisioning/login → secure and conversational structured onboarding →
validated completion → version lifecycle → AI generation → own current-plan
view → own-context AI chat → approved adaptation → later client modules`.

The original secure-link/form flow remains alongside conversational onboarding
until a later approved decision replaces it.

### 8.3 Sequência sugerida para o Codex

Esta ordem é uma orientação de execução adicionada nesta consolidação; não altera a composição do MVP.

| Etapa | Trabalho | Referências principais |
| --- | --- | --- |
| 1 | Conciliar decisões que afetem a primeira entrega e preparar a estrutura tecnológica necessária. | DEC-01, DEC-03, DEC-04, DEC-05, TEC-01 a TEC-10 e RNF04/RNF06. |
| 2 | Implementar autenticação, autorização, cadastro e consulta de clientes. | RF-04, RF-05, RF-01, RF-02 e RF-03. |
| 3 | Implementar convites por e-mail e formulário de onboarding com isolamento de dados. | RF-09, RF-10, RF-11, RF-12 e RF-13. |
| 4 | Implementar a primeira ficha, visualização e versionamento, junto dos fluxos profissionais necessários. | RF-15, RF-16, RF-17 e RN-12 a RN-19. |
| 5 | Implementar chat e propostas de adaptação, preservando aprovação e histórico. | RF-18, RF-19, RN-16 a RN-18 e RN-29 a RN-31. |
| 6 | Verificar o percurso completo do MVP e os critérios não funcionais aplicáveis. | Critérios dos RF incluídos, RNF01 a RNF06 e regras pertinentes. |
| 7 | Implementar os demais módulos em tarefas específicas conforme a prioridade definida para o projeto. | Demais RF, incluindo a decisão sobre RF-24X/RF-25X e RN-37. |

### 8.4 Scope classification

| Major feature | Classification | Governing requirements/decisions |
| --- | --- | --- |
| Client/account CRUD, auth, authorization | Original MVP; Tasks 02–06 implemented/integration-verified | RF-01–RF-05; DEC-03–DEC-05, DEC-17 |
| Secure-link structured onboarding | Original MVP; planned | RF-09–RF-13; DEC-06, DEC-18 |
| Conversational onboarding | Approved MVP extension; planned | EXT-RF-AI-01; DEC-06, DEC-08, DEC-18 |
| Training generation/version/current view/chat/adaptation | Original MVP; planned | RF-15–RF-19; DEC-07, DEC-08, DEC-15, DEC-18 |
| Employee management, recovery, onboarding self-review | Original post-MVP; not started | RF-06–RF-08, RF-14 |
| Progress sharing | Approved post-MVP extension; planned | EXT-RF-SOC-01; EXT-DEC-SOC-01 |
| Equipment management/catalog | Original post-MVP; planned | RF-32, RF-33 |
| Equipment quantity | Approved post-MVP extension; planned | EXT-RF-EQP-01; EXT-DEC-EQP-01 |
| Access/attendance/anonymous occupancy | Original post-MVP; occupancy blocked | RF-20–RF-25X; DEC-09–DEC-11 |
| Named visible presence | Approved post-MVP extension; blocked | EXT-RF-PRES-01; DEC-10, EXT-DEC-PRES-01 |
| Billing/plans/dashboard/classes | Original post-MVP; not started | RF-26–RF-31; DEC-12–DEC-14 |
| CA-03.4 biometric readiness | Deferred, not satisfied | RF-03/CA-03.4, RF-22, DEC-05 |

## 9 Approved and unresolved decisions

`docs/decisions.md` is the chronological authority. This section replaces the
historical presentation of every DEC as unresolved.

| ID | Status | Canonical result or remaining question | Affected work |
| --- | --- | --- | --- |
| DEC-01 | Unresolved; non-blocking while original scope is used | Professor validation may later change scope. Preserve all original requirements and the explicit original MVP meanwhile. | Overall scope; no independent task is blocked. |
| DEC-02 | Unresolved | Meaning of the `X` suffix in RF-24X/RF-25X. Do not infer cancellation. | Occupancy tasks. |
| DEC-03 | **Resolved** | Python/FastAPI modular monolith, PostgreSQL/SQLAlchemy/Alembic, React/TS/Vite/MUI, Keycloak/OIDC, SMTP/Mailpit, Docker Compose/Linux/UFW, provider-independent AI adapters, and approved pinned baseline. NestJS has no MVP role. | All architecture and external adapters. |
| DEC-04 | **Resolved for current roles/provisioning** | Roles are client, employee, attendant, instructor, admin. Initial admin is environment-bootstrapped; clients are administratively provisioned with only client role; future employees use an administrative flow. Health/biometric access follows section 2.1. | Auth, clients, health, training, future employees. |
| DEC-05 | **Resolved** | `account_active` controls application login only; `gym_access_enabled`/physical eligibility is separate. CA-03.4 remains explicitly deferred to RF-22 and unsatisfied. | RF-03/RF-04 and future physical access. |
| DEC-06 | Partially resolved | Invitation tokens are 24-hour, client-bound, purpose-bound, hashed, single-use on intentional redemption, and superseded by resends. Schema, required fields/types/units/ranges, editability, and recovery-token policy remain unresolved. | Task 07 may proceed; Tasks 08–11 and EXT-RF-AI-01 remain blocked by their relevant unresolved portions. |
| DEC-07 | Unresolved; blocking | Health severity criteria, proposal/review/approval states, approvers, and activation rules. | Training generation/adaptation. |
| DEC-08 | Unresolved; blocking | AI provider/model, contracts, structured outputs, context limits, retention/error behavior. | Conversational onboarding, RF-15, RF-18, RF-19. |
| DEC-09 | Unresolved | Biometric confidence/accuracy semantics, measurement, thresholds, and below-threshold behavior. | RF-21/RF-22. |
| DEC-10 | Unresolved; blocking occupancy implementation | Relationship/source of truth between access-event presence and auxiliary camera counts, spaces, freshness, and failure behavior. | RF-24X/RF-25X, RN-37, EXT-RF-PRES-01. |
| DEC-11 | Unresolved | Access-integration payload/auth/idempotency, recognition versus authorization/release, alternatives and manual override. | RF-20–RF-23. |
| DEC-12 | Unresolved | Plan/enrollment/payment model, validity/modalities/access allowance, confirmation, renewal, delinquency and purchasable plans. | RF-31, RN-22/RN-24/RN-35/RN-36. |
| DEC-13 | Unresolved | Financial meanings and calculations, periods and filters; profit is not automatically revenue. | RF-26–RF-29. |
| DEC-14 | Unresolved | Class recurrence, visibility, reservation/capacity and authorized exceptions. | RF-30/RN-25. |
| DEC-15 | Unresolved; blocking where invoked | Manual/review training, exercise maintenance, evaluations, completed workouts, critical notices, audit/export flows. | RF-15–RF-19 and related RN. |
| DEC-16 | Unresolved; blocking formal RNF sign-off | Reference load, timeouts, viewports, usability protocol and continuous-availability measurement. | Formal end-to-end RNF verification. |
| DEC-17 | **Resolved for identity/client model** | Independent Account and Client UUIDs; unique normalized Account e-mail and unique nullable Keycloak subject; one-to-one Account↔Client; no local credentials. Other domain slices remain to be decided before their migrations. | Client/identity now; later domain schemas. |
| DEC-18 | Unresolved; blocking sensitive-data work | Health/biometric storage, access, logging, retention, replacement and audit-evidence policy. | Health onboarding, AI health context, biometrics. |

DEC-19 is a later approved decision, not an original question: it records the
client-facing direction and the four extension requirements in section 3.1.

### 9.1 Extension decision gates

| ID | Status | Required decision | Expected task |
| --- | --- | --- | --- |
| EXT-DEC-SOC-01 | Unresolved; blocking | Shared audience semantics, moderation, deletion, and retention. | Controlled progress sharing. |
| EXT-DEC-EQP-01 | Unresolved; blocking persistence design | Canonical logical type/model and individual-unit versus aggregate inventory representation. | Equipment catalog and quantities. |
| EXT-DEC-PRES-01 | Unresolved; blocking | Consent lifecycle, visible fields, source/freshness, revocation, staff access, and retention for named presence. | Opt-in visible presence. |

### 9.2 Privacy and sensitive-data rules

| Data category | Access and handling boundary |
| --- | --- |
| Account/profile | Owner and explicitly authorized administrative operations; normalized e-mail is account-owned. Client lists remain administrative. |
| Health/onboarding | Client and only staff with functional need; attendants and admin status alone do not grant medical access. Apply RN-11/RN-23 and DEC-18. |
| Biometrics | Separate from ordinary profile data; authorized biometric staff only; never common reports or social/presence views. Apply RN-10/RN-34. |
| Authentication | Keycloak owns credentials. Tokens/secrets are not stored as domain data or logged. Subject is an external reference only. |
| Financial | Client's own allowed view and explicitly authorized operations only; never social or presence content. |
| Progress/social | Author-owned; visibility is explicit. No sensitive category is automatically copied into a post. |
| Attendance/presence | Anonymous occupancy is distinct from named opt-in presence. Identifiable events require approved operational access and privacy rules. |
| AI context | Minimum permitted context for the resolved authenticated client only. Never cross-client; no diagnosis; sensitive prompts/responses are not unnecessarily logged. |

No retention duration is invented. RN-18/RN-27/RN-33 historical and audit
preservation applies where relevant, subject to an approved sensitive-data
retention decision.

### 9.3 Current implementation status

Status is evidence-based from completed tasks and their tests, not inferred from
unchecked boxes or planned files.

| Requirement | Scope | Status | Dependency/decision | Notes |
| --- | --- | --- | --- | --- |
| Foundation | Enabler | Implemented | DEC-03 | Task 01 verified baseline. |
| RF-04 | Original MVP | Implemented | DEC-03–DEC-05 | Task 02; Task 06 integration verifies real provisioned clients. |
| RF-05 | Original MVP | Implemented | DEC-04 | Task 03; client-role denial reverified in Task 06. |
| RF-01/RF-02 | Original MVP | Implemented | DEC-04/DEC-17 | Task 04 plus Task 06 provisioning integration. |
| RF-03 | Original MVP | **Partially implemented** | DEC-05 | CA-03.1–CA-03.3 implemented; CA-03.4 deferred and not satisfied. |
| Client identity provisioning | Approved DEC integration | Implemented | DEC-03/04/05/17 | Task 06: client-only Keycloak identity, subject linkage, required action, and independent durable reconciliation. |
| RF-09 | Original MVP | Implemented | DEC-03/DEC-04/DEC-06/DEC-17 | Task 07: provisioned active client, hashed 24-hour invitation, SMTP outcome persistence, resend invalidation. |
| RF-10–RF-13 | Original MVP | Planned | DEC-06/DEC-18 | Tasks 08–09 and 11; not yet implemented. |
| EXT-RF-AI-01 | Approved MVP extension | Planned | DEC-06/08/18 | Task 10; not yet implemented. |
| RF-15–RF-19 | Original MVP | Planned | DEC-07/08/15/18 | Tasks 12–16 after renumbering. |
| MVP integrated verification | Original MVP verification | Planned | DEC-16 | Task 17. |
| EXT-RF-SOC-01 | Approved post-MVP extension | Planned | EXT-DEC-SOC-01 | Task 18. |
| RF-32/RF-33 + EXT-RF-EQP-01 | Original post-MVP + extension | Planned | EXT-DEC-EQP-01 | Task 19. |
| RF-23–RF-25X | Original post-MVP | Planned/blocked | DEC-10/DEC-11 | Task 20 implements count/view only after decisions. |
| EXT-RF-PRES-01 | Approved post-MVP extension | Blocked | DEC-10/EXT-DEC-PRES-01 | Task 21. |
| Remaining RF-06–RF-08, RF-14, RF-20–RF-22, RF-26–RF-31 | Original post-MVP | Not started | Applicable DEC items | Preserved; no implementation claim. |

## 10 Fluxo de trabalho do Codex

### 10.1 Historical task-model constraints

- Delimitar a funcionalidade, o módulo e os arquivos ou pastas que podem ser alterados.
- Não alterar camadas, Docker, autenticação, banco ou frontend quando estiverem fora do escopo da tarefa.
- Não adicionar novas dependências sem justificar e solicitar aprovação.
- Criar ou ajustar apenas os testes relacionados à funcionalidade.
- Rodar apenas os testes relacionados à tarefa.
- The source requested a completion response of at most 10 lines. Current
  `AGENTS.md` and task-file completion requirements govern the actual report
  format while preserving the same required content.

### 10.2 Modelo de tarefa com rastreabilidade

O modelo abaixo mantém a estrutura do anexo e acrescenta referências aos identificadores deste arquivo. Substituir os campos entre colchetes a cada tarefa.

```text
Tarefa: implementar [funcionalidade específica].

Contexto:
- Ler AGENTS.md e docs/requirements.md.
- Consultar requirements.md para proveniência original, docs/decisions.md para
  decisões cronológicas e docs/product-extensions.md para extensões aprovadas.
- O sistema possui [módulos relevantes].
- A funcionalidade pertence ao módulo [nome].
- Requisitos funcionais: [RF-XX].
- Requisitos não funcionais: [RNFXX].
- Regras de negócio: [RN-XX].
- Decisões já registradas: [DEC-XX e a decisão correspondente].

Escopo permitido:
- Alterar somente [arquivos/pastas].
- Não alterar [camadas ou módulos fora da tarefa].
- Não adicionar dependências sem justificar e solicitar aprovação.

Comportamento esperado:
1. [Comportamento ligado ao requisito].
2. [Comportamento ligado ao requisito].

Critérios de aceitação:
- [CA-XX.Y e condição verificável].
- [CA-XX.Z e condição verificável].

Testes:
- Criar ou ajustar apenas testes relacionados à funcionalidade.
- Rodar apenas os testes relacionados.
- Registrar o resultado e informar o que não foi possível verificar.

Resposta final:
- No máximo 10 linhas.
- Informar arquivos alterados, testes executados e pendências.
```

### 10.3 Conclusão de uma tarefa

Considerar uma tarefa concluída quando os critérios de aceitação previstos para ela forem verificados, as regras de negócio pertinentes forem respeitadas, os testes relacionados tiverem resultado registrado e as limitações remanescentes estiverem explícitas. Marcar apenas os critérios efetivamente atendidos; manter os demais pendentes.

## 11 Terminal unresolved-decision index

Only genuinely unresolved items appear here. Their full questions, impact, and
expected tasks are in section 9 and the implementation plan. Do not resolve them
by inference.

- **DEC-01:** professor-validated final scope; non-blocking while preserving the
  original catalog/MVP.
- **DEC-02:** RF-24X/RF-25X suffix meaning; affects occupancy work.
- **DEC-06:** onboarding schema/editability and recovery-token policies; its
  invitation-token policy is approved for Task 07, while remaining portions
  block Tasks 08–11.
- **DEC-07:** AI health severity and review/approval lifecycle; blocks training
  generation/adaptation tasks.
- **DEC-08:** AI provider and contracts; blocks conversational onboarding and AI
  training/chat/adaptation tasks.
- **DEC-09:** biometric metrics and thresholds; blocks relevant RF-21/RF-22 work.
- **DEC-10:** occupancy source/meaning/freshness; blocks Task 20 and contributes
  to the Task 21 block.
- **DEC-11:** physical-access integration and exceptions; blocks RF-20–RF-23.
- **DEC-12:** plans, enrollment, payment, and entry eligibility details; blocks
  RF-31 and related physical-access work.
- **DEC-13:** financial indicator meanings; blocks RF-28/RF-29 financial metrics.
- **DEC-14:** class scheduling/capacity/reservation model; blocks RF-30 details.
- **DEC-15:** manual/review/exercise/audit flows; blocks the affected training
  tasks when those flows are required.
- **DEC-16:** RNF measurement protocol; blocks formal Task 17 sign-off.
- **DEC-18:** sensitive-data storage/access/retention/logging; blocks health/AI
  and biometric work.
- **EXT-DEC-SOC-01:** sharing audience and lifecycle; blocks Task 18.
- **EXT-DEC-EQP-01:** equipment grouping/inventory model; blocks Task 19's
  persistence design.
- **EXT-DEC-PRES-01:** named-presence consent/data/source/retention model; blocks
  Task 21 together with DEC-10.
