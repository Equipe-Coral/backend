# Projeto Coral – Documento Mestre

**Subtítulo:** Ecossistema de Inteligência Legislativa, Educação Cívica e Pressão Cidadã Rastreadas.

---

## 1. O Problema (A Dor)

O Brasil possui uma das maiores estruturas de dados públicos e de participação digital do mundo, mas sofre com um abismo gigantesco entre **dados disponíveis** e **engajamento cívico real**.

1. **O Abismo da Linguagem ("Juridiquês"):**

   * Textos de leis, projetos e regulamentos são herméticos, técnicos e longos.
   * O cidadão não consegue responder às perguntas básicas: *“O que está sendo decidido?”*, *“Isso me afeta como?”*.

2. **Sensação de Impotência e Caixa-Preta:**

   * Reclamações em canais oficiais (ouvidorias, apps públicos) muitas vezes somem em fluxos burocráticos.
   * A pessoa não vê retorno, não sabe se foi lida, se virou algo concreto – isso gera apatia.

3. **Desconhecimento de Quem é o Alvo Correto:**

   * Cidadão culpa o prefeito por problema que é de lei antiga.
   * Cobra o vereador errado (que nem tem base no bairro dele).
   * Não distingue bem o que é responsabilidade municipal, estadual ou federal.

**Resumo:**
O cidadão **quer participar**, mas não sabe **o que** está sendo votado, **como** isso o afeta, **quem** pressionar, nem **o que acontece depois** que ele apoia uma ideia ou reclama.

---

## 2. Contexto e Premissas para o MVP

Para o MVP (Hackathon), assumimos as seguintes premissas de realidade e escopo:

1. **Interface Zero-Fricção:**

   * O canal de entrada deve ser onde o brasileiro já está: **WhatsApp**.
   * A jornada começa num chat 1:1 com um bot, por texto ou áudio.

2. **Não haverá integração profunda com contas governamentais (MVP):**

   * Integrações com apps como *Descomplica* e plataformas oficiais exigem autenticação do cidadão, protocolos formais e regras específicas.
   * Para um Hackathon, isso é pesado e arriscado. Em vez disso:

     * Toda reclamação gera também um registro interno na plataforma Coral.
     * As interações com plataformas oficiais serão **assistidas** (passo-a-passo) e não automatizadas.

3. **Dados existem, mas estão dispersos:**

   * APIs da Câmara, Senado, TSE, diários oficiais, portais de transparência e iniciativas como **Querido Diário** e **Base dos Dados**.
   * Problema não é falta de dado, é **costurar** isso de forma compreensível e acionável.

4. **Atenção é escassa:**

   * Ninguém vai ler um PDF de 50 páginas.
   * A informação precisa chegar em formato “snack”: resumo, antes/depois, impacto no bolso, áudio curto.

5. **Política é local e concreta:**

   * Engajamento aumenta quando o problema é sentido na pele: bairro, linha de ônibus, escola, UBS.

---

## 3. Visão Geral da Solução

**Coral** é uma plataforma **multiagente de inteligência cívica** que atua como um **tradutor e organizador** entre a rua e o gabinete.

Nós **não** somos apenas um app de denúncia nem apenas um espelho do e-Cidadania. Somos um sistema que:

1. **Escuta** o problema do cidadão (texto/áudio via WhatsApp).
2. **Classifica e Agrupa** relatos em diferentes níveis de alcance usando IA (modelo de 3 camadas de jurisdição).
3. **Investiga** causas e contexto usando dados públicos (leis, PLs, orçamento, contratos, histórico de votação).
4. **Traduz** legislação complexa em linguagem cidadã (Educação Legislativa personalizada).
5. **Organiza a pressão** de forma **coletiva e rastreável**, priorizando números, histórico e relatórios – e não apenas “cards de pressão”.
6. **Registra** a trilha das ações em uma **camada de confiança (blockchain)** para garantir integridade, autoria cívica e prova de existência.

---

## 4. O Modelo de 3 Camadas (A "Cebola" da Jurisdição)

O agrupamento de casos é **elástico**. A IA analisa o relato do cidadão e define uma tag `scope_level` que posiciona o caso em uma das três camadas.

### 4.1. Nível 1 – Hiper-Local (Bairro / Raio de 1 km)

* **O que é:**

  * Problemas físicos, pontuais, de **zeladoria urbana**.
* **Exemplos:**

  * Buraco na rua.
  * Lixo acumulado numa esquina.
  * Poste de iluminação queimado na praça.
  * Bar vizinho fazendo barulho de madrugada.
* **Quem resolve:**

  * Subprefeitura, administração regional, Secretaria de Obras/Serviços.
* **Lógica de agrupamento:**

  * **Geo-spatial clustering**: relatos com coordenadas (ou endereços) próximos se agrupam em um mesmo caso.
* **Por que funciona:**

  * O vizinho da rua de cima se importa; o morador do outro lado da cidade não.

### 4.2. Nível 2 – Serviço / Região (Cross-Bairro)

* **O que é:**

  * Problemas sistêmicos que afetam **vários bairros**, mas não se resumem a um único ponto físico.
* **Exemplos:**

  * **Transporte:** A linha de ônibus 40 atende 5 bairros. Atrasos constantes não são do “bairro X”, são da **linha 40**.
  * **Saúde:** Falta de médicos em uma UBS que atende toda uma região.
* **Quem resolve:**

  * Secretarias Municipais (Transporte, Saúde, Educação, etc.).
* **Lógica de agrupamento:**

  * Por **entidade afetada** (ID da linha de ônibus, ID da escola, ID da UBS).

### 4.3. Nível 3 – Cidade / Estado (Macro / Temático)

* **O que é:**

  * Temas que extrapolam um bairro ou serviço e viram **política pública, direito ou orçamento**.
* **Exemplos:**

  * “Merenda escolar ruim em várias escolas.”
  * “Guarda municipal violenta.”
  * “Queremos uma lei que proíba fogos de artifício barulhentos.”
* **Quem resolve:**

  * Prefeito, Câmara Municipal, Governador, eventualmente Legislativo estadual ou federal.
* **Lógica de agrupamento:**

  * Por **tópico/tema** (merenda, segurança pública, meio ambiente, direitos de pessoas com deficiência etc.).

### 4.4. Como a IA usa o Modelo de Camadas

1. A IA recebe o relato e extrai:

   * Local (texto + geolocalização, quando disponível).
   * Entidade/serviço afetado (escola X, linha de ônibus Y etc.).
   * Tema de fundo (mobilidade, saúde, educação, meio ambiente…).

2. Com base nesses elementos, o sistema:

   * Define `scope_level` (1, 2 ou 3).
   * Agrupa o relato em um **caso existente** ou cria um **novo caso**.

3. O efeito disso no produto:

   * Evitar 80 reclamações idênticas espalhadas; elas viram **1 caso com 80 apoiadores/relatos**.
   * Facilitar a escolha do **alvo correto** (subprefeitura vs. secretaria vs. Câmara).
   * Gerar relatórios e dossiês que fazem sentido para o poder público.

---

## 5. Fluxos de Interação

### 5.1. Fluxo Base – Conversa 1:1 pelo WhatsApp

1. **Entrada do relato:**

   * Cidadão envia texto ou áudio com a reclamação ou ideia.

2. **Transcrição e normalização:**

   * Áudio é transcrito (Whisper) e padronizado.
   * IA identifica:

     * Tipo: reclamação, sugestão de lei, elogio, dúvida.
     * Local.
     * Tema.

3. **Classificação na Cebola da Jurisdição:**

   * IA atribui `scope_level` (1, 2 ou 3).

4. **Detecção de caso existente:**

   * O sistema busca casos ativos com o mesmo `scope_level` e alta similaridade de tema/local/serviço.
   * Cenários:

     * **Caso similar encontrado:** o relato entra como **novo relato dentro do mesmo caso**; o cidadão é convidado a **apoiar** e seguir o andamento.
     * **Nada similar:** cria-se um **novo caso** na plataforma interna.

A partir daí, o fluxo se divide em dois grandes caminhos:

* **Caminho A:** Não existe PL/lei/ação governamental mapeada sobre o tema.
* **Caminho B:** Já existe PL, legislação ou ação relacionada.

---

## 5.2. Caminho A – Quando NÃO existe PL, Lei ou Ação Governamental Relacionada

### 5.2.1. Coleta da Opinião do Cidadão

Se, após consulta às bases de dados, a IA não encontra nada relevante (sem PL ativo, lei específica, nem programa público sobre o tema):

1. A IA explica, em linguagem simples:

   * “Olha, hoje não encontramos nenhuma lei ou projeto específico tratando disso.”

2. Em seguida, pede a opinião da pessoa:

   * “Se você pudesse decidir, como você gostaria que isso fosse resolvido?”

3. A IA ajuda a transformar essa fala em uma **proposta estruturada**, em três camadas:

   * Versão cidadã (linguagem simples).
   * Versão técnica resumida (para burocracia).
   * Tags de tema e escopo (para agrupamento futuro).

### 5.2.2. Registro na Rede Interna e Co-autoria Coletiva

4. O sistema cria ou atualiza um **caso na plataforma Coral** contendo:

   * Relato(s).
   * Proposta em linguagem cidadã.
   * Rascunho em linguagem técnica (juridiquês suave).
   * Escopo (`scope_level`) e tags.

5. O cidadão recebe um **link para o caso na nossa rede**:

   * Pode rever o texto, comentar, compartilhar.
   * Pode ver casos similares de outras pessoas.

6. Outros usuários, ao navegarem na plataforma, podem:

   * **Apoiar** o caso.
   * Comentar, complementar com evidências, documentos, fotos.

7. A ausência de co-autoria em plataformas oficiais (como e-Cidadania) é contornada internamente:

   * No Coral, o caso é explicitamente uma **proposta coletiva**, com contagem de apoiadores e registros de quem participou.
   * Se futuramente a ideia virar uma sugestão legislativa formal, o documento resultante é uma **síntese coletiva**, não só de um autor.

### 5.2.3. Critérios para Abertura de um Dossiê

Um **dossiê** é um nível acima de um simples caso. Ele é aberto quando o problema atinge relevância suficiente para justificar um pacote formal de pressão.

Critérios possíveis (parametrizáveis por camada):

* **Quantidade:**

  * Mínimo de `N` relatos únicos + `M` apoiadores no mesmo caso.
* **Tempo:**

  * Persistência do problema por mais de `X` semanas/meses sem resposta.
* **Gravidade:**

  * Casos envolvendo violação de direitos fundamentais, violência, riscos à vida.
* **Escopo:**

  * Casos Nível 3 (cidade/estado) com dispersão geográfica grande.

Quando o limiar é alcançado, o dossiê é gerado automaticamente:

1. **Conteúdo do Dossiê:**

   * Narrativa factual do problema (linha do tempo de relatos).
   * Dados agregados (mapas, estatísticas, evolução de apoio).
   * Propostas coletivas estruturadas.
   * Análise jurídica da IA (leis relacionadas, lacunas, referências internacionais, quando aplicável).
   * Sugestões de caminhos: ofício administrativo, projeto de lei, recomendação a órgãos de controle.

2. **Registro em Blockchain (Prova de Existência):**

   * Gera-se um PDF do dossiê.
   * Calcula-se um hash (SHA-256) e registra-se em uma rede EVM (Polygon/Base).
   * Isso garante que o documento pode ser verificado como não alterado posteriormente.

3. **Encaminhamento:**

   * O dossiê é enviado para os alvos adequados (secretarias, gabinetes, Ministério Público, etc.), conforme o escopo.
   * Cada envio gera evento na blockchain: *“Dossiê X encaminhado à Secretaria Y em DD/MM/AAAA”*.

4. **Transparência:**

   * O caso e o dossiê ganham um **painel de status** na plataforma:

     * Encaminhado para quem.
     * Quando.
     * Se houve resposta.

### 5.2.4. Integração com Ideias Legislativas em Plataformas Oficiais

Aqui entra uma **decisão crítica de design**:

* **Não é viável e nem estrategicamente ideal**, no MVP, tentar “empurrar” automaticamente tudo para e-Cidadania ou apps como Descomplica, por vários motivos:

  * Exigem login do cidadão.
  * Regras de uso nem sempre permitem automação massiva.
  * Não existe co-autoria: fica o nome de uma pessoa, o que dilui o caráter coletivo.

**Estratégia do Coral:**

1. Quando o caso atinge certo nível de maturidade, a IA pode sugerir:

   * “Essa proposta também pode virar uma ideia legislativa oficial. Você quer registrar?”

2. Se o cidadão quiser:

   * A plataforma gera:

     * Um texto em juridiquês (proposta formal).
     * Um resumo cidadão (para divulgação).
   * Envia um **passo-a-passo** e um **vídeo curto** mostrando como registrar a ideia na plataforma oficial.

3. O cidadão registra por conta própria e, se quiser, marca na plataforma:

   * “Registrei como Ideia Legislativa no site X.”

4. A partir daí, o sistema passa a **monitorar** o identificador dessa proposta (quando tecnicamente possível) e, sempre que houver mudança de status (virou PL, arquivado, aprovado, etc.), notifica o cidadão e os apoiadores do caso.

> Resultado: o Coral **potencializa** as plataformas oficiais existentes, sem depender juridicamente delas e mantendo o registro coletivo e rastreado internamente.

---

## 5.3. Caminho B – Quando JÁ existe PL, Lei ou Ação Relacionada

Neste caso, o valor central é **Educação Legislativa personalizada + organização da pressão**.

### 5.3.1. Descoberta e Mapeamento

1. A IA consulta APIs da Câmara, Senado, legislação municipal/estadual e bases locais.
2. Identifica:

   * PLs em tramitação relacionados ao tema.
   * Leis já existentes.
   * Programas e ações do Executivo.

### 5.3.2. Tradução Legislativa (Agente Pedagogo)

Em vez de jogar um link de lei ou PL, o sistema responde em **linguagem cidadã**, sem viés, respondendo ao que importa na vida real do usuário.

Outputs típicos:

1. **Metáfora explicativa:**

   * “Esse projeto de lei funciona como um ‘cheque especial’ para a Prefeitura…”

2. **Antes e Depois:**

   * Tabelas simples ou comparações diretas:
   * “Hoje: você espera até 3 meses pela resposta.
     Com a nova lei: o órgão teria prazo máximo de 15 dias.”

3. **Impacto no Bolso e na Rotina:**

   * “Atualmente, cerca de 30% do preço do seu remédio é imposto. Esse PL quer reduzir essa carga. Se aprovado, um remédio de R$ 100 pode cair para aproximadamente R$ 70.”

4. **Contexto de Tramitação (para dar senso de processo):**

   * Fase em que o PL está.
   * Quais comissões analisam.
   * Quem é o autor e quem pode destravar o processo.

### 5.3.3. Coleta da Opinião da Pessoa

Depois de explicar:

1. A IA pergunta:

   * “Você é a favor, contra, ou tem uma sugestão diferente?”

2. A resposta é transformada em:

   * Um **texto estruturado** (respeitando o conteúdo original, sem enviesar).
   * Tags de posição (a favor / contra / sugerindo ajustes específicos).

### 5.3.4. Decisões de Encaminhamento Interno

Aqui havia dúvidas importantes que o fluxo precisa resolver. Proposta:

1. **Regra-base:**

   * **Toda interação gera uma ação interna**, mas **nem sempre** um novo caso.

2. Se já existe um caso na plataforma relacionado àquele PL/lei:

   * O sistema pergunta algo como:

     * “Já temos um caso sobre isso com X pessoas apoiando. Você prefere apoiar esse caso ou abrir um caso separado com um recorte diferente (por exemplo, apenas para o seu bairro)?”
   * Se a pessoa escolhe **apoiar**, sua opinião é registrada como:

     * Mais um apoiador.
     * Mais um depoimento/argumento, se ela quiser.

3. Se não existe caso relacionado:

   * Cria-se um **novo caso** referente àquele PL/tema.

4. Em ambos os cenários, o cidadão pode escolher:

   * **Apenas receber atualizações** sobre aquele PL/caso.
   * **Participar mais ativamente**, enviando evidências, relatos etc.

### 5.3.5. Encaminhamento Externo Assistido (sem automatizar tudo)

Ao invés de tentar enviar automaticamente comentários para o site da Câmara/Senado (o que é juridicamente arriscado e tecnicamente complexo), o Coral funciona como um **co-piloto cívico**:

1. Sugere ações:

   * “Você pode comentar diretamente no projeto de lei no site oficial.”
   * “Você pode escrever para o gabinete do(a) vereador(a)/deputado(a) responsável.”

2. Gera:

   * Um texto base em juridiquês (comentário formal).
   * Um texto em linguagem simples (explicando a posição).

3. Envia para o usuário:

   * O texto pronto para copiar/colar.
   * Um **vídeo curto** mostrando como comentar naquele PL ou usar a plataforma oficial.

4. Pergunta ao final:

   * “Você conseguiu enviar seu comentário?”
   * Se **sim**, o sistema registra uma **ação externa** associada ao perfil da pessoa e ao caso.

> Crítica incorporada: não faz sentido tentar automatizar envio direto a partir do Coral sem conhecer todas as regras das plataformas oficiais e sem ter autenticação. Melhor empoderar o cidadão e registrar a intenção/ação.

### 5.3.6. Rastreamento do que acontece com o PL

Mesmo que o comentário tenha sido postado em outra plataforma, o Coral pode cuidar de **monitorar o andamento**:

1. O caso fica atrelado ao identificador do PL.
2. O sistema acompanha mudanças de status (andou de comissão, foi arquivado, aprovado, vetado etc.).
3. Sempre que houver mudança relevante, os usuários que marcaram “quero acompanhar” recebem atualização pelo canal preferido (WhatsApp, e-mail, app).

Assim, respondemos ao problema original: hoje as pessoas apoiam ideias em plataformas públicas e **não sabem o que aconteceu depois**.

### 5.3.7. Dossiê em Casos com PL Existente

Se um PL específico passa a concentrar muitos relatos e apoios dentro do Coral:

* Também pode gerar um **dossiê temático**, contendo:

  * Histórico do PL.
  * Linha do tempo de engajamento dos cidadãos.
  * Principais argumentos pró e contra vindos da base.
  * Recomendações de ajustes.

Esse dossiê também é registrado em blockchain e pode ser encaminhado aos atores relevantes (gabinetes, comissões, imprensa, organizações da sociedade civil).

---

## 6. Estratégia de Pressão: Menos Card, Mais Evidência e Rastro

O projeto original cogitava forte uso de **cards de pressão** (imagens) como principal forma de mobilização. Após análise crítica:

* **Pressão baseada só em imagem não é a melhor estratégia**, especialmente para um MVP de hackathon:

  * Demanda tempo de design.
  * Gera ruído nas redes sem necessariamente gerar resposta institucional.
  * Pode ser facilmente diluída no fluxo de notícias.

**Reformulação da estratégia:**

1. **Foco no rastro documental e numérico:**

   * Contagem pública de relatos e apoiadores.
   * Dossiês com dados, mapas, linhas do tempo.
   * Ofícios formais e relatórios padronizados.

2. **Card como apoio, não como pilar:**

   * Podemos gerar assets visuais simples (imagem com texto, sem depender de IA de imagem) para facilitar compartilhamento.
   * Mas a pressão principal se ancora em **números, relatórios e protocolos registrados**.

3. **Valor para o poder público:**

   * Em vez de só “exposição” nas redes, o Coral entrega **insumos utilizáveis**: séries históricas, clusters geográficos, síntese de demandas por secretaria.

---

## 7. Identidade Cívica e Camada de Confiança (Blockchain)

Para que a participação tenha peso e confiabilidade, o sistema cria um **ID Cívico** para cada usuário.

1. **Registro do usuário:**

   * Validação leve (telefone, e-mail, eventualmente outros fatores em fases futuras).
   * Gera um identificador único.

2. **Tudo é ação cívica rastreável:**

   * Criar caso.
   * Apoiar caso.
   * Comentar.
   * Confirmar envio de ideia em plataforma externa.
   * Encaminhamentos e respostas do poder público.

3. **Blockchain como trilha imutável:**

   * Para cada caso/dossiê e seus marcos importantes, registra-se um hash em rede EVM (Polygon/Base).
   * Não se grava dados pessoais nem texto integral, apenas o hash e metadados mínimos.

4. **Benefícios:**

   * Provar que um caso existia em determinada data (importante contra apagões burocráticos).
   * Demonstrar que determinada demanda teve X apoiadores e foi enviada ao órgão Y em tal data.

---

## 8. Arquitetura Tecnológica Resumida

| Módulo                   | Função                                  | Tecnologia / API                         |
| ------------------------ | --------------------------------------- | ---------------------------------------- |
| **Interface**            | Chatbot & notificações                  | WhatsApp Business API (Twilio/Meta)      |
| **Orquestração**         | Workflow entre agentes                  | LangChain ou n8n                         |
| **Agente Ouvinte**       | Transcrição e limpeza de áudio          | OpenAI Whisper                           |
| **Agente Classificador** | Escopo (3 camadas) + tema + duplicidade | LLM + embeddings + geocoding             |
| **Agente Pedagogo**      | Simplificação de leis e PLs             | LLM (GPT/Claude) + APIs Câmara/Senado    |
| **Agente Investigador**  | Dados eleitorais, contratos, orçamento  | CSV/JSON TSE + Querido Diário + BD       |
| **Gestor de Casos**      | Casos, apoios, dossiês, status          | Backend (Node/TS, Python, etc.)          |
| **Agente Ativista**      | Geração de textos, ofícios, resumos     | LLM + templates HTML/PDF                 |
| **Trust Layer**          | Prova de existência e ações             | Smart Contracts (Solidity, Polygon/Base) |
| **Frontend Web**         | Painel do cidadão, mapa, busca de casos | React / Next.js + Tailwind CSS           |

> Observação: geração de imagem por IA (DALL·E etc.) passa a ser opcional e periférica, não núcleo da pressão.

---

## 8.1. Mapa de Calor Cívico (Demandas Visuais)

O **mapa de calor** é a principal forma visual de enxergar, em tempo real, onde as demandas estão se concentrando na cidade.

1. **Fonte de dados do mapa:**

   * Cada relato e cada apoio em um caso possui:

     * Localização (endereços geocodificados ou coordenadas aproximadas).
     * `scope_level` (1, 2 ou 3).
     * Tema (mobilidade, saúde, educação, etc.).
   * O backend agrega essas informações para gerar camadas de calor (heatmaps) por tema, por período de tempo e por nível de escopo.

2. **Camadas do mapa de calor:**

   * **Camada Hiper-local (Nível 1):**

     * Pontos de zeladoria urbana (buracos, lixo, iluminação, ruído) viram manchas de calor em ruas específicas.
     * Útil para subprefeituras e equipes de campo.
   * **Camada Serviço/Região (Nível 2):**

     * Problemas de um mesmo serviço (linha de ônibus, UBS, escola) aparecem agregados como "manchas" maiores, com indicação da entidade (ex.: Linha 40).
   * **Camada Cidade/Estado (Nível 3):**

     * Temas macro (merenda, violência da guarda, direitos difusos) geram um pano de fundo de calor que mostra a dispersão geográfica das reclamações.

3. **Visão do Cidadão:**

   * No painel web, a pessoa pode:

     * Ver onde existem casos abertos perto dela.
     * Filtrar por tema (ex.: só educação, só transporte).
     * Clicar em um “ponto quente” e abrir o caso correspondente para apoiar, comentar ou acompanhar.
   * Isso reforça a noção de **coletividade**: “não sou só eu reclamando, tem muita gente com o mesmo problema”.

4. **Visão do Poder Público e da Sociedade Civil:**

   * Órgãos públicos, organizações e imprensa podem usar o mapa para:

     * Identificar áreas com maior concentração de problemas.
     * Cruzar calor de demandas com limites administrativos (distritos, bairros, regionais, etc.).
     * Priorizar inspeções, políticas e respostas onde a pressão cívica está mais intensa.
   * Dossiês podem incluir capturas ou versões estáticas do mapa de calor, mostrando a geografia da demanda.

> Em resumo, o mapa de calor transforma a massa de relatos e apoios em uma **fotografia visual da pressão cidadã**, conectando diretamente o modelo de 3 camadas com uma ferramenta intuitiva para quem participa e para quem precisa responder.

---

## 9. Riscos, Limitações e Cuidados

1. **Neutralidade e viés:**

   * A tradução legislativa deve ser explicativa, não militante.
   * O sistema deve mostrar, sempre que possível, prós e contras das propostas.

2. **Privacidade e segurança de dados:**

   * Minimizar dados pessoais na camada on-chain.
   * Garantir que o cidadão sabe o que está sendo registrado e por quê.

3. **Dependência de fontes externas:**

   * APIs podem mudar, sair do ar ou ter limitações.
   * É importante tratar falhas de dados de forma transparente (“não foi possível consultar agora”).

4. **Risco de frustração:**

   * Mesmo com rastreio, o poder público pode não responder.
   * Mitigação: ser honesto sobre limites; oferecer caminhos alternativos (imprensa, órgãos de controle, conselhos de políticas públicas).

---

## 10. Como o Coral Responde ao Desafio

> **Problema do desafio:** Como a IA pode ser utilizada para aumentar o engajamento cidadão em discussões legislativas e governamentais, garantindo que pessoas comuns se informem, compreendam, se sintam ouvidas e influenciem as leis que impactam suas vidas?

**1. Informar:**

* Agente Pedagogo traduz PLs, leis e programas em linguagem simples, com metáforas, exemplos, antes/depois e impacto concreto.
* A explicação é personalizada pelo bairro, profissão, uso do serviço público.

**2. Fazer compreender:**

* Modelo de 3 camadas ajuda a pessoa a entender se o problema é da rua, do serviço ou da cidade/Estado.
* Mostra quem é o alvo correto (subprefeitura, secretaria, Câmara, Governo) e em que etapa está o processo.

**3. Fazer a pessoa se sentir ouvida:**

* Cada relato vira parte de um caso com contagem de apoiadores.
* Abertura de dossiês mostra que a demanda coletiva vira um documento sério, não só um desabafo.
* Registro em blockchain garante que a voz não desapareça.

**4. Influenciar leis e políticas:**

* Quando não há PL, o sistema ajuda a coletar e estruturar uma proposta legislativa coletiva.
* Quando há PL, o sistema educa, organiza posicionamentos e apoios e orienta a ação em plataformas oficiais.
* Dossiês e relatórios focados em secretarias e gabinetes aumentam a chance de resposta institucional.
