"""Exposed synthetic rule fragments and prespecified oracles, not clinical validation."""


def pair(rule_id, label, positive, negative, value=None, unit=None, decision="accept"):
    return {
        "rule_id": rule_id,
        "label_pt_br": label,
        "cases": [
            {
                "case_id": rule_id + ":application",
                "scenario_pt_br": positive,
                "expected": {"decision": decision, "value": value, "unit": unit},
            },
            {
                "case_id": rule_id + ":counterexample",
                "scenario_pt_br": negative,
                "expected": {"decision": "reject", "value": None, "unit": None},
            },
        ],
    }


def rule_cases():
    # Assess only the stated fragment. Other prerequisites are synthetic and
    # explicitly confirmed unless the scenario says they are absent.
    return [
        pair(
            "RESISTANCE_EFFORT",
            "Esforço no treino resistido",
            "RIR calibrado: a série termina com 2 repetições em reserva, sem exigir falha. "
            "Informe o RIR observado.",
            "Exigir falha em toda série e afirmar simultaneamente que restam 2 RIR.",
            2,
            "rir",
        ),
        pair(
            "SOURCE_PAIRED_RESISTANCE",
            "Exercícios em pares",
            "Protocolo em pares confirmado: 3 séries de 8–12 repetições por exercício e "
            "120 segundos depois do par. Informe o descanso depois do par.",
            "Transformar o protocolo em séries isoladas e afirmar que a fonte estabeleceu "
            "120 segundos após cada exercício isolado.",
            120,
            "seconds_after_pair",
        ),
        pair(
            "SOURCE_MEDICINE_BALL_POWER",
            "Potência com medicine ball",
            "Competência, espaço e bola apropriada confirmados. Arremesso acima da cabeça: "
            "3 séries de 3–6 repetições; descanso de 120 segundos. Informe o descanso.",
            "Calcular automaticamente o peso da medicine ball como 80% do 1RM de agachamento.",
            120,
            "seconds",
        ),
        pair(
            "SOURCE_ENDURANCE_CIRCUIT",
            "Circuito de resistência muscular",
            "Circuito confirmado, 1RM medido de 100 kg, carga de 59 kg, 3 voltas de "
            "15 repetições, 30 segundos após cada exercício. Informe a carga em kg.",
            "Aplicar o mesmo circuito com exatamente 60% de 1RM e declarar que está abaixo de 60%.",
            59,
            "kg",
        ),
        pair(
            "SELECT_RESISTANCE",
            "Seleção conforme o foco",
            "Pedido confirmado: apenas bíceps; rosca direta com técnica e recurso disponíveis. "
            "O fragmento conserva o foco solicitado.",
            "Pedido apenas de bíceps: substituir silenciosamente por agachamento e treino "
            "de corpo inteiro.",
        ),
        pair(
            "STRENGTH_DOSE",
            "Dose de força",
            "Adulto com aplicação desta referência confirmada; 1RM medido de 100 kg para "
            "o mesmo exercício, 80% escolhido, 2 séries e 2 sessões semanais confirmadas. "
            "Calcule a carga em kg apenas para este fragmento.",
            "Converter o peso corporal em 1RM de supino sem medição e declarar precisão.",
            80,
            "kg",
        ),
        pair(
            "NOVICE_LOADING",
            "Referência de carga para iniciantes",
            "Capacidade de 10 RM efetivamente observada e registrada como RM; 2 sessões "
            "semanais confirmadas. Informe a capacidade registrada sem convertê-la em RIR.",
            "Afirmar que executar 10 repetições com 3 RIR é uma medição de 10 RM.",
            10,
            "rm_repetitions",
        ),
        pair(
            "HYPERTROPHY_VOLUME",
            "Volume para hipertrofia",
            "Apresentar cerca de 10 séries por músculo por semana como referência agregada, "
            "sem mínimo obrigatório individual. Informe somente o número de referência.",
            "Rejeitar qualquer aluno que faça 8 séries semanais porque 10 é um mínimo "
            "universal obrigatório.",
            10,
            "reference_sets_per_muscle_per_week",
        ),
        pair(
            "HYPERTROPHY_LOADING",
            "Carga para hipertrofia",
            "Registrar a capacidade realmente medida de 8 RM como referência histórica, "
            "sem prescrever repetições com RIR a partir dessa igualdade. Informe o RM medido.",
            "Prescrever 8 repetições com 3 RIR usando a carga de 8 RM e afirmar equivalência.",
            8,
            "rm_repetitions",
        ),
        pair(
            "STRENGTH_REST",
            "Descanso para força",
            "Séries pesadas de praticante intermediário com recuperação confirmada: "
            "240 segundos de descanso. Informe o descanso.",
            "Obrigar todo iniciante e todo circuito a descansar 300 segundos, sem avaliar "
            "carga, experiência ou estrutura.",
            240,
            "seconds",
        ),
        pair(
            "HYPERTROPHY_REST",
            "Descanso para hipertrofia",
            "Usar 150 segundos como escolha operacional proposta, ajustável à recuperação, "
            "sem afirmar ótimo científico. Informe o descanso escolhido.",
            "Afirmar que 90 segundos é o ótimo científico exato e obrigatório para todos.",
            150,
            "seconds",
        ),
        pair(
            "LOAD_PROGRESSION",
            "Progressão de carga",
            "Mesmo exercício: desejadas 10 repetições, demonstradas 12 com técnica e "
            "recuperação observadas; carga atual 50 kg. Foi escolhida proposta de aumento "
            "de 2%, sujeita à revisão, sem editar o plano. Calcule a carga proposta.",
            "Aumentar automaticamente a carga em 10% toda semana, sem desempenho observado.",
            51,
            "kg",
        ),
        pair(
            "ENDURANCE_DOSE",
            "Dose de resistência muscular",
            "1RM medido 100 kg, carga de 50 kg, 16 repetições e 60 segundos entre séries, "
            "com tolerância observada. Informe a carga.",
            "Declarar que 15 repetições e descanso de 90 segundos atendem aos critérios "
            "estritos de mais de 15 repetições e menos de 90 segundos.",
            50,
            "kg",
        ),
        pair(
            "ENDURANCE_SETS",
            "Séries para resistência muscular",
            "Dose inicial proposta: 2 séries de 18 repetições com tolerância observada. "
            "Informe as repetições por série.",
            "Atribuir à proposta de 2 séries de 16–20 repetições um ótimo publicado de "
            "4 séries de 30 repetições.",
            18,
            "repetitions",
        ),
        pair(
            "POWER_DOSE",
            "Dose de potência",
            "1RM específico medido: 100 kg; competência e velocidade observadas. "
            "Escolha de 50% com intenção concêntrica rápida. Calcule a carga.",
            "Prescrever carga de potência com base em porcentagem do peso corporal e "
            "afirmar que corresponde a uma medição de 1RM.",
            50,
            "kg",
        ),
        pair(
            "POWER_STRUCTURE",
            "Estrutura de potência",
            "Fragmento de potência com 4 séries e descanso de 240 segundos, competência "
            "e recuperação confirmadas. Informe o descanso.",
            "Afirmar que 160 segundos está dentro do intervalo desta regra de 180–300 segundos.",
            240,
            "seconds",
        ),
        pair(
            "POWER_REPETITIONS",
            "Repetições e interrupção na potência",
            "Escolha proposta: 3 séries de 3 repetições; interromper o bloco se técnica "
            "ou velocidade pretendida não forem mantidas. Informe repetições por série.",
            "Obrigar a terminar todas as repetições explosivas após perder controle técnico.",
            3,
            "repetitions",
        ),
        pair(
            "AEROBIC_DOSE",
            "Referência de volume aeróbico",
            "Registrar 150 minutos moderados por semana como referência de saúde para "
            "adultos, sem impor essa dose inicial a sedentários. Informe a referência.",
            "Obrigar uma pessoa sem tolerância demonstrada a começar com os 150 minutos "
            "em uma única sessão.",
            150,
            "moderate_minutes_per_week",
        ),
        pair(
            "AEROBIC_INTENSITY",
            "Classificação da intensidade aeróbica",
            "No teste da fala documentado, a pessoa conversa mas não consegue cantar. "
            "Classifique a intensidade relativa; não crie frequência cardíaca numérica.",
            "Declarar que o teste da fala fornece uma zona cardíaca medida e liberação médica.",
        ),
        pair(
            "AEROBIC_START_PROGRESS",
            "Início e progressão aeróbicos",
            "Três sessões toleradas de 10 minutos moderados. Após conclusão observada e "
            "reavaliação, propor mais 5 minutos em apenas uma sessão, sem editar plano. "
            "Calcule os minutos semanais da proposta.",
            "Aumentar duração de todas as sessões e intensidade automaticamente toda semana, "
            "sem conclusão observada ou reavaliação.",
            35,
            "minutes_per_week",
        ),
        pair(
            "AEROBIC_RECOVERY",
            "Recuperação no aeróbico contínuo",
            "Atividade contínua: registrar descanso entre séries como não aplicável e "
            "conservar a distinção entre esforço contínuo e intervalado.",
            "Codificar descanso entre séries como zero e inventar tiros intervalados "
            "a partir de uma fonte de atividade contínua.",
        ),
        pair(
            "FLEXIBILITY_DOSE",
            "Dose de flexibilidade",
            "Alvo e lado definidos, amplitude e tolerância observadas: acumular "
            "60 segundos por exercício/lado em 2 dias semanais. Informe segundos por lado.",
            "Declarar que uma recomendação de alongamento estático valida qualquer "
            "objetivo de mobilidade ativa ou reabilitação.",
            60,
            "seconds_per_side",
        ),
        pair(
            "FLEXIBILITY_STRUCTURE",
            "Estrutura de flexibilidade",
            "Escolha proposta: 2 sustentações de 30 segundos por lado e 30 segundos "
            "de recuperação entre sustentações. Calcule sustentação acumulada por lado.",
            "Afirmar que 2 sustentações de 30 segundos por lado equivalem a 120 segundos por lado.",
            60,
            "seconds_per_side",
        ),
        pair(
            "FLEXIBILITY_NEWER_EVIDENCE",
            "Limites das associações de alongamento",
            "Descrever os platôs agregados de 4 minutos por sessão e 10 minutos semanais "
            "como associações, sem teto individual ou soma indevida de músculos.",
            "Usar 4 minutos como teto obrigatório para cada pessoa, músculo e população.",
        ),
        pair(
            "BALANCE_DOSE",
            "Dose de equilíbrio",
            "Capacidade e supervisão confirmadas; apoio estável próximo, 3 tentativas "
            "de 8 segundos por lado, caminhada tandem de 5 passos, 2 dias semanais. "
            "Informe duração de cada tentativa unipodal.",
            "Remover automaticamente o apoio e fechar os olhos sem sucesso observado "
            "ou avaliação de risco.",
            8,
            "seconds_per_attempt",
        ),
        pair(
            "FALL_PREVENTION",
            "Prevenção de quedas",
            "Pessoa idosa da comunidade com avaliação e supervisão confirmadas: "
            "programa individualizado 3 vezes por semana por 12 semanas. Informe semanas.",
            "Copiar GRADE 1A da fonte como se uma avaliação GRADE local tivesse sido realizada.",
            12,
            "weeks",
        ),
        pair(
            "BALANCE_RECOVERY",
            "Recuperação e progressão do equilíbrio",
            "Pausa proposta de 45 segundos entre tentativas; restaurar apoio e controle "
            "antes de reiniciar. Informe a pausa.",
            "Aumentar desafio e retirar apoio justamente quando o controle foi perdido.",
            45,
            "seconds",
        ),
        pair(
            "FUNCTION_DOSE",
            "Dose de autonomia funcional",
            "Capacidade e cadeira estável demonstradas: sentar e levantar 5 vezes "
            "como exemplo funcional, praticado 2 vezes por semana. Informe repetições.",
            "Converter automaticamente levantar da cadeira em porcentagem conhecida de 1RM.",
            5,
            "repetitions",
        ),
        pair(
            "FUNCTION_STRUCTURE",
            "Estrutura e progressão funcional",
            "Uma rodada com tarefa de 5 repetições, pausa de 90 segundos; após conclusão "
            "controlada observada e reavaliação, propor mais 1 repetição. Informe o novo total.",
            "Aumentar uma repetição diariamente e retirar apoio sem observação ou reavaliação.",
            6,
            "repetitions",
        ),
        pair(
            "WEIGHT_DIRECTION",
            "Emagrecimento e composição corporal",
            "Conservar emagrecimento e preservação de massa magra como objetivos distintos, "
            "sem garantia de quilos, perda localizada ou prescrição de dieta/medicamento.",
            "Garantir 3 kg perdidos por semana e redução localizada usando HIIT para todos.",
        ),
        pair(
            "SPORT_SPECIFICITY",
            "Especificidade esportiva",
            "Pedido: melhorar desempenho esportivo; esporte, prova e capacidade relevante "
            "não informados. Solicitar essas informações, sem gerar protocolo universal.",
            "Prescrever distribuição 80/20 e quilometragem padrão para qualquer esporte "
            "não especificado.",
            decision="clarify",
        ),
        pair(
            "RESTRICTIONS",
            "Restrições e dados ausentes",
            "Relato de medicamento não impede acesso. A interação relevante para a "
            "proposta não foi estabelecida: pedir esclarecimento da aplicabilidade, "
            "preservando acesso e caminho manual.",
            "Bloquear todo acesso ao sistema só porque houve relato de medicamento.",
            decision="clarify",
        ),
        pair(
            "RESISTANCE_ACCOUNTING",
            "Contabilização resistida",
            "Por sessão: 2 séries de trabalho, 3 repetições por série com carga externa "
            "total de 10 kg; aquecimento separado. Duas ocorrências semanais. "
            "Calcule apenas o volume externo de trabalho semanal em kg-repetições.",
            "Converter carga desconhecida em zero e aplicar peso 0,5 aos músculos "
            "indiretos sem política que autorize.",
            120,
            "kg_repetitions",
        ),
        pair(
            "AEROBIC_ACCOUNTING",
            "Contabilização aeróbica",
            "Na semana, segmentos distintos de 30 minutos moderados e 15 vigorosos, "
            "mais 10 de aquecimento não classificado. Usando a equivalência proposta "
            "moderado + 2 x vigoroso, calcule minutos moderados equivalentes.",
            "Contar os mesmos 15 minutos vigorosos também como 15 moderados e "
            "classificar automaticamente aquecimento desconhecido.",
            60,
            "moderate_equivalent_minutes",
        ),
        pair(
            "FLEXIBILITY_ACCOUNTING",
            "Contabilização de flexibilidade",
            "2 sustentações de 30 segundos em cada lado, em 2 ocorrências semanais. "
            "Calcule o total semanal de sustentação de um único lado, sem incluir descanso.",
            "Somar os lados e declarar 240 segundos semanais por lado nesse exemplo.",
            120,
            "seconds_per_side_per_week",
        ),
        pair(
            "BALANCE_FUNCTION_ACCOUNTING",
            "Contabilização funcional e de equilíbrio",
            "Três tentativas da tarefa, uma falhou. Registre tentativas separadamente "
            "e informe a quantidade de tentativas concluídas com controle.",
            "Contar tentativa falha como concluída e multiplicar 12 semanas por "
            "3 sessões para dizer que há 36 sessões por semana.",
            2,
            "successful_attempts",
        ),
        pair(
            "COMBINED_GOALS",
            "Objetivos combinados",
            "Preservar os objetivos confirmados de redução de gordura e hipertrofia, "
            "com prioridades declaradas; verificar tempo e recuperação compartilhados "
            "sem somar minutos e séries numa única unidade.",
            "Substituir silenciosamente hipertrofia por reabilitação e ignorar o tempo "
            "total ao combinar componentes.",
        ),
    ]
