# Requisitos do Sistema de Controle de Academia

Documento de referência para orientar o desenvolvimento do sistema pelo Codex. Reúne todos os requisitos funcionais, critérios de aceitação, requisitos não funcionais, regras de negócio e tecnologias presentes no anexo.

**Fonte:** `Codex-Requisitos (teste academia)(1).docx`, Universidade Federal de Goiás, Engenharia de Computação, EMC, setembro de 2026.

**Cobertura:** 33 requisitos funcionais com 110 critérios de aceitação, 6 requisitos não funcionais com 18 critérios de aceitação, 37 regras de negócio e 10 entradas da tabela de tecnologias. Também estão registrados o MVP informado, as restrições técnicas dispersas no texto e os pontos que precisam de definição.

**Estado:** especificação consolidada para planejamento. As caixas de critérios de aceitação estão desmarcadas porque este arquivo não comprova implementação ou testes do sistema.

## 1 Contexto e orientação de uso

### 1.1 Objetivo do sistema

Centralizar e automatizar as operações administrativas, financeiras e de atendimento de uma academia, melhorando o controle do estabelecimento e o processo de elaboração de fichas de treino específicas para cada cliente.

O domínio inclui cadastro de clientes e funcionários, autenticação e permissões, onboarding, fichas de treino e interações com IA, biometria e controle de acesso, frequência e lotação, cobranças e planos, indicadores administrativos, aulas e equipamentos.

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
| DEC-01 a DEC-18 | Pendências identificadas nesta consolidação; não são decisões já aprovadas. |

Os requisitos e critérios foram reorganizados com ajustes de grafia, sem supressão de condições. As notas de implementação, a sequência sugerida e as pendências são orientações desta consolidação e estão identificadas como tais.

### 1.3 Instruções para o Codex

1. Ler este arquivo antes de planejar uma funcionalidade e identificar os RF, RNF, RN e critérios de aceitação afetados.
2. Trabalhar no escopo da tarefa atual. Usar o MVP da seção 8 como referência de prioridade, respeitando suas dependências e pendências.
3. Aplicar as regras de negócio e os requisitos não funcionais pertinentes mesmo quando a tarefa mencionar apenas um RF.
4. Não transformar alternativas tecnológicas, itens condicionais ou dúvidas do anexo em decisões silenciosas. Resolver apenas as pendências que afetem a tarefa; avançar no trabalho independente delas.
5. Preservar os identificadores para permitir rastrear tarefas, alterações e validações até os requisitos.
6. Usar as caixas de aceitação como acompanhamento: marcar um item somente depois de implementá-lo e verificar seu comportamento.
7. Não ampliar o escopo por inferência de um diagrama ou pela existência de uma regra sem fluxo funcional detalhado. Registrar a necessidade e relacioná-la à decisão correspondente.
8. Seguir as restrições de trabalho e o modelo de tarefa da seção 10.

## 2 Atores e responsabilidades mencionados

| Ator ou termo | Responsabilidade indicada no anexo |
| --- | --- |
| Cliente ou aluno | Preencher e consultar seus dados, acessar ficha e chat, comprar plano e consultar informações disponibilizadas pela academia. |
| Atendente | Realizar atividades de atendimento e cadastrar foto facial do cliente conforme permissões. |
| Instrutor, professor ou profissional | Avaliar sugestões da IA, modificar fichas e montar treinos manualmente; permanecer identificado como responsável pelo que criou ou alterou. |
| Administrador ou usuário administrativo | Executar as operações administrativas previstas, conforme autorização. |
| Funcionário | Categoria usada nos requisitos de cadastro e autorização; inclui responsabilidades que precisam ser distribuídas entre os perfis operacionais. |
| Visitante | Consultar equipamentos disponíveis, conforme RF-33. |

Esta tabela descreve os atores citados. A matriz completa de permissões, a relação entre funcionário e seus subperfis e a equivalência entre instrutor/professor/profissional dependem de DEC-04.

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

### 6.1 Tecnologias indicadas no anexo

A fonte apresenta esta lista como “Tecnologia recomendada”. Ela é a referência tecnológica do projeto, mas contém alternativas explícitas que ainda precisam de escolha. Não há versões de bibliotecas, runtimes, serviços ou ferramentas fixadas no documento.

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

As escolhas não especificadas devem ser tratadas conforme DEC-03, DEC-08, DEC-09, DEC-10, DEC-11 e DEC-12. Não acrescentar dependências ou fornecedores como se constassem da fonte.

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

### 7.2 Limites de arquitetura

A fonte menciona diagramas de MER e microsserviços e indica arquitetura modular no backend. As imagens incorporadas concentram-se em entidades e relacionamentos; não estabelecem uma divisão inequívoca dos serviços, seus contratos ou sua implantação.

Portanto, a fronteira entre módulos e processos, a distribuição de responsabilidades entre NestJS e Python, a autenticação escolhida e o desenho de implantação precisam ser registrados em DEC-03. O requisito de desacoplamento das integrações permanece válido em qualquer solução adotada.

## 8 MVP e sequência de implementação

### 8.1 MVP explicitamente informado

O anexo inclui os seguintes 15 requisitos no MVP:

`RF-01`, `RF-02`, `RF-03`, `RF-04`, `RF-05`, `RF-09`, `RF-10`, `RF-11`, `RF-12`, `RF-13`, `RF-15`, `RF-16`, `RF-17`, `RF-18` e `RF-19`.

O caminho crítico informado é:

Cadastro → Acesso → E-mail → Onboarding → Geração por IA → Ficha → Chat → Adaptação dinâmica.

Essa lista não dispensa os RNF e RN associados aos requisitos escolhidos.

### 8.2 Dependências que precisam ser conciliadas

| Dependência | Implicação para o MVP |
| --- | --- |
| RF-03 exige foto válida para clientes habilitados, enquanto RF-22 não integra o MVP. | Definir como ocorre a habilitação inicial e em que etapa a biometria será necessária; DEC-05. |
| RF-09 exige infraestrutura de e-mail. | Definir envio e tratamento de falha antes de validar os convites, mesmo que recuperação de acesso por RF-06 fique para outra entrega. |
| RF-15 e RF-19 dependem de contexto de saúde e aprovação de alterações. | Definir bloqueios, revisão e versionamento junto de RN-12 a RN-19; DEC-07. |
| RN-14 e RN-19 exigem edição integral pelo professor e montagem manual de treino. | Detalhar como esses fluxos se encaixam na entrega que usar IA; não considerá-los implementados apenas porque RF-15 está pronto. |
| RF-04 e RF-05 pressupõem usuários e permissões disponíveis. | Definir o provisionamento inicial e a matriz de permissões; DEC-04. |

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

## 9 Pendências e conflitos a resolver no contexto da tarefa

Esta seção não acrescenta requisitos aprovados. Ela registra informações ausentes ou divergentes que podem mudar a implementação. Resolver a pendência quando ela afetar o trabalho atual e registrar a decisão no projeto; não interromper tarefas independentes.

| ID | Tema | Definição necessária |
| --- | --- | --- |
| DEC-01 | Escopo validado com o professor | A observação inicial diz que vários itens podem estar incorretos ou fora do pedido. Identificar quais serão mantidos, adiados ou alterados e qual é a entrega vigente. Até essa definição, preservar o catálogo e a lista de MVP informada. |
| DEC-02 | Sufixo X | Esclarecer o significado de RF-24X e RF-25X. Não inferir que estejam excluídos, cancelados ou concluídos. |
| DEC-03 | Decisões tecnológicas e arquitetura | Definir Keycloak/OIDC ou autenticação integrada; SMTP ou API de e-mail e sua relação com CA-06.4; responsabilidades de NestJS e Python; módulos ou serviços; firewall, ambiente de execução e versões. A fonte não escolhe ORM, biblioteca visual, hospedagem nem ferramentas específicas de teste. |
| DEC-04 | Perfis e provisionamento | Definir a matriz de permissões de administrador, atendente, instrutor e demais funcionários; quem altera biometria; quem acessa saúde; equivalência dos termos professor/instrutor; criação do primeiro administrador e das contas necessárias ao MVP. |
| DEC-05 | Estados de conta e habilitação | Distinguir conta ativa, cliente habilitado, foto biométrica válida, pagamento confirmado e matrícula válida. Conciliar RF-03, RF-04, RF-22 e RF-31, incluindo a possibilidade de o cliente acessar onboarding e compra antes da liberação da entrada física. |
| DEC-06 | Onboarding e tokens | Definir o formulário aprovado, campos obrigatórios, tipos, unidades e validações, período de edição e atualização após conclusão; definir duração e uso dos tokens de convite e recuperação. O anexo menciona uma reunião e um formulário aprovado sem apresentar essas definições completas. |
| DEC-07 | IA, saúde e aprovação | Definir como reconhecer casos que bloqueiam a geração, quais validações serão usadas, quem revisa e aprova, quais estados uma proposta percorre e quando passa a ser ficha vigente. Conciliar geração inicial, modificação integral pelo professor e a proibição de alteração silenciosa. |
| DEC-08 | Provedor e contrato da IA | Escolher provedor/modelo e definir estrutura da ficha, contexto enviado, contrato de resposta, validações, tratamento de erro e comportamento em indisponibilidade, respeitando a separação de dados entre clientes. |
| DEC-09 | Métricas de biometria | Esclarecer se 95% significa precisão do modelo ou confiança por reconhecimento; definir como medir e aplicar o mínimo citado, o limiar de qualidade da foto e o tratamento de resultados abaixo do limiar. |
| DEC-10 | Origem e significado da lotação | RF-24X/RF-25X contam presença por catraca; RN-37 conta pessoas por câmeras em espaços específicos. Definir se as visões coexistem ou se há substituição, qual dado cada tela usa, espaços, frequência de atualização e comportamento quando a contagem falhar. |
| DEC-11 | Integração de acesso e exceções | Definir payload, autenticação e identificador de evento; separar reconhecimento, decisão e liberação da catraca; especificar o fluxo alternativo de RN-08 e a liberação manual com responsável e motivo de RN-09. |
| DEC-12 | Planos, matrícula e pagamento | Definir modalidades, quantidade e período dos acessos permitidos, relação entre assinatura/matrícula, datas e horários de validade, confirmação pela API, renovação e eventual bloqueio por inadimplência. Definir também como os planos ativos serão disponibilizados para compra. |
| DEC-13 | Indicadores financeiros | Definir fatura, faturamento, cobrança, valor recebido e lucro, além de períodos e filtros. O anexo cita lucro, mas não descreve a origem de despesas ou custos; não calcular lucro como sinônimo automático de receita. |
| DEC-14 | Agenda e capacidade | Definir ocorrência pontual versus recorrência, visibilidade pública ou autenticada, eventual reserva, limite de participantes e ação excepcional autorizada. RF-30 não detalha o fluxo de reservas citado condicionalmente em RN-25. |
| DEC-15 | Fluxos mencionados apenas em regras | Detalhar montagem manual e revisão de fichas, manutenção de exercícios, avaliações, registro de treinos executados, avisos de alterações críticas, auditoria e eventuais exportações. RN-20, RN-21, RN-26, RN-27 e RN-28 não especificam sozinhas telas ou operações completas. |
| DEC-16 | Medição dos RNF | Definir condições normais e carga de referência para o limite de 2 segundos, tempos de espera externos, dispositivos/resoluções suportados, tarefas de usabilidade e forma de verificar a disponibilidade contínua com manutenção programada. O documento não fixa percentual mensal de disponibilidade. |
| DEC-17 | Modelo de dados de referência | Conciliar os diagramas, nomes, cardinalidades, campos e vínculos; definir assinatura/matrícula e como interações, propostas, itens e versões se relacionam. Relacionar responsável pela ficha, validade e modalidade aos requisitos antes das migrações correspondentes. |
| DEC-18 | Retenção e tratamento de dados sensíveis | Definir armazenamento separado de biometria, descarte da foto substituída, acesso a saúde, dados permitidos em logs e avisos, retenção e preservação da evidência de auditoria sem manter indevidamente a foto descartada. |

## 10 Fluxo de trabalho do Codex

### 10.1 Restrições presentes no modelo de tarefa do anexo

- Delimitar a funcionalidade, o módulo e os arquivos ou pastas que podem ser alterados.
- Não alterar camadas, Docker, autenticação, banco ou frontend quando estiverem fora do escopo da tarefa.
- Não adicionar novas dependências sem justificar e solicitar aprovação.
- Criar ou ajustar apenas os testes relacionados à funcionalidade.
- Rodar apenas os testes relacionados à tarefa.
- Encerrar a tarefa com resposta de no máximo 10 linhas, informando arquivos alterados, testes executados e pendências.

### 10.2 Modelo de tarefa com rastreabilidade

O modelo abaixo mantém a estrutura do anexo e acrescenta referências aos identificadores deste arquivo. Substituir os campos entre colchetes a cada tarefa.

```text
Tarefa: implementar [funcionalidade específica].

Contexto:
- Ler REQUISITOS.md.
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
