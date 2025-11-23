## 1. Blocos de dados que o Coral precisa

Pensando no que você já desenhou, o Coral depende de:

1. **Dados legislativos**

   * Textos e metadata de PLs, leis, PLS, PEC etc.
   * Tramitação, comissões, votações, autores.

2. **Dados de representantes e eleições**

   * Quem representa quem (deputados, vereadores etc.).
   * Resultados de votação por seção/bairro.

3. **Dados de orçamento, contratos e programas**

   * “Tem dinheiro pra isso?”
   * Quem contratou quem, pra fazer o quê, por quanto.

4. **Dados de participação e reclamações**

   * Fala.BR, ouvidorias, e-Cidadania, e-Democracia, estatísticas.

5. **Diários oficiais e atos administrativos**

   * Licitações, contratos, decretos, portarias, nomeações.

6. **Dados geográficos e demográficos**

   * Malhas territoriais, setores censitários, população por bairro/município.

7. **Catálogos de dados** (pra descobrir mais fontes)

   * dados.gov.br, Base dos Dados, catálogos de APIs do gov.br.

---

## 2. Principais fontes públicas, o que elas entregam e pra quê servem no Coral

### 2.1. Legislativo Federal – Câmara dos Deputados

**Fonte:** Dados Abertos da Câmara (API REST oficial) ([dadosabertos.camara.leg.br][1])

* **Base URL:** `https://dadosabertos.camara.leg.br/api/v2/`
* **Documentação:** Swagger da API (explorador online). ([dadosabertos.camara.leg.br][1])

**Endpoints centrais pro Coral:**

* `/proposicoes`

  * Busca PLs, PECs etc. por tipo, número, ano, palavras-chave.
* `/proposicoes/{id}`

  * Detalhe de uma proposição (ementa, inteiro teor, situação, links).
* `/proposicoes/{id}/tramitacoes`

  * Histórico de tramitação, com datas e órgãos.
* `/proposicoes/{id}/votacoes` e `/votacoes/{id}/votos`

  * Quem votou como, placar, data.
* `/deputados`, `/deputados/{id}`

  * Dados sobre parlamentares (nome, partido, UF, e-mail, redes, etc.).

**Como vem a informação:**

* Por padrão, **JSON**, com dois campos principais:

  * `dados`: lista de objetos (cada proposição, deputado, etc.).
  * `links`: paginação (`rel`, `href`).
* Exemplo de campos em `proposicoes`:

  * `id`, `uri`, `siglaTipo`, `numero`, `ano`, `ementa`, `statusProposicao`. ([dadosabertos.camara.leg.br][2])

**Uso no Coral:**

* Agente Pedagogo puxa o texto e contexto oficial do PL.
* Agente Investigador cruza PLs com temas/territórios.
* Para Nível 3 (cidade/estado/país), ajuda a vincular demandas a PLs federais.

---

### 2.2. Legislativo e Normas – Senado + LexML

**Senado – Dados abertos:** catálogo geral ([Senado Federal][3])

* O Senado tem diversos conjuntos de dados (projetos, votações, senadores, etc.) listados no catálogo. ([Senado Federal][3])

**LexML – API para acervo legislativo e normativo** ([Senado Federal][4])

* **O que é:** portal que unifica normas, PLs, jurisprudência de várias casas.
* **API:** segue o padrão **SRU** (Search/Retrieval via URL), retornando **XML**.
* **Uso típico:**

  * Montar URL com parâmetros de busca (palavras-chave, ano, tipo de norma).
  * A API devolve XML com metadados da norma: título, data, tipo, origem, URIs.

**Uso no Coral:**

* Quando você quer ir além da Câmara e trazer:

  * Leis já aprovadas.
  * Normas correlatas (municipais/estaduais, quando indexadas).
* Bom para o Agente Investigador montar o quadro jurídico completo de um tema.

---

### 2.3. Representação e Eleições – TSE

**Portal de Dados Abertos do TSE:** ([Portal de Dados Abertos do TSE][5])

* Reúne conjuntos de dados de eleições (incluindo 2024).
* Dados vêm em **ZIP** com **CSV/TXT** de milhões de linhas.

Exemplo importante para o Coral:

* Conjunto **“Resultados 2024”** – inclui arquivos de votação por seção eleitoral. ([Portal de Dados Abertos do TSE][6])

  * Campos típicos: UF, município (com código IBGE), zona, seção, cargo, número do candidato, nome do candidato, partido, votos etc.

**Uso no Coral:**

* Construir a **“Geometria política”**:

  * A partir do endereço do cidadão → localizar a seção/zona (isso exige algum mapeamento externo ou manual).
  * Agregar os votos por candidato em um recorte espacial (por bairro, conjunto de seções).
  * Descobrir **“Top 3 vereadores/deputados na sua região”**.
* Esses dados são brutos: você lê o CSV com Python/Pandas, junta com malha de seções/bairros (IBGE + dados locais) e gera o mapa de “quem tem base onde”.

---

### 2.4. Orçamento, Despesas e Contratos – Portal da Transparência + Tesouro

**Portal da Transparência – API REST** ([Portal da Transparência][7])

* **Base:** `https://api.portaldatransparencia.gov.br/` (documentação em Swagger).
* **Autenticação:** precisa de **chave de API (token)**:

  * Fazer cadastro via gov.br para gerar o token. ([Portal da Transparência][8])
  * Token vai no header HTTP (ex.: `chave-api-dados`).

**Principais recursos:**

* **Despesas públicas:** por órgão, programa, função, etc. ([Portal da Transparência][9])
* **Contratos, convênios, licitações.**
* **Servidores, viagens, benefícios.**

**Formato:**

* Retorno em **JSON**, geralmente como lista de objetos (cada registro de despesa/contrato).
* Campos típicos: órgão, unidade, CNPJ da empresa, valor empenhado/pago, data, função, programa.

**Tesouro Transparente – API de Custos** ([Tesouro Transparente][10])

* Traz dados de **custos por órgão/atividade**, também em formato aberto (API).
* Complementa o Portal da Transparência com visão de custo por área de política pública.

**Uso no Coral:**

* Validar se “não tem dinheiro” é argumento real:

  * Existe dotação orçamentária? Quanto foi gasto? Com quem?
* Alimentar dossiês com:

  * “Nos últimos 3 anos, a Secretaria X empenhou R$ Y em limpeza urbana nesta região e mesmo assim o serviço não foi entregue.”

---

### 2.5. Diários Oficiais – Querido Diário

**Querido Diário (OKBR)** ([docs.queridodiario.ok.org.br][11])

* **O que é:** projeto que raspa e unifica **diários oficiais municipais** em uma API pública.
* **Docs da API:**

  * Visão geral da API pública. ([docs.queridodiario.ok.org.br][12])
  * Swagger: `https://api.queridodiario.ok.org.br/docs` ([api.queridodiario.ok.org.br][13])

**Como acessar:**

* Endpoint típico (exemplo geral):

  * `GET /gazettes` com filtros:

    * `territory_id` (código IBGE do município).
    * `since` / `until` (datas).
    * `query` (palavras-chave no texto).
* Retorno em **JSON**:

  * Cada “gazette” vem com: `territory_id`, `published_at`, `url`, `excerpt`, `power` etc.

**Uso no Coral:**

* Descobrir **atos executivos** relevantes para o problema reportado:

  * Licitação para tapa-buraco.
  * Contrato com empresa de coleta de lixo.
  * Decretos que afetem o serviço.
* Alimentar o Agente Investigador com “o que já foi decidido/contratado que não chegou na ponta”.

---

### 2.6. Participação e Reclamações – Fala.BR, e-Cidadania, e-Democracia

#### Fala.BR (Ouvidoria + Acesso à informação)

* **Plataforma integrada de manifestações e pedidos de informação** do Executivo Federal. ([Fala.BR][14])

**Dados abertos agregados (sem login):**

* Conjunto “Fala.BR – módulo acesso à informação” em dados.gov.br: estatísticas de pedidos LAI e recursos. ([Dados Abertos][15])

  * Formato: CSV; campos de órgão, data, tipo de pedido, situação etc.

**API Fala.BR (mais poderosa, mas com atrito):**

* Documentação de API: permite **cadastrar, consultar e tratar manifestações** via integração. ([Fala.BR][16])
* Necessita credenciais e acordo de uso (é mais para integração de sistemas de governo).

**Uso no Coral (MVP):**

* Mais viável:

  * Usar os **dados agregados** para enriquecer dossiês (ex.: “órgão X é recordista em reclamações nessa área”).
* Evitar, num primeiro momento, integração de escrita via API (complexa juridicamente e exige governança).

---

#### e-Cidadania (Senado) – Ideias Legislativas e Consultas Públicas

* Portal oficial para ideias legislativas e consultas sobre PLs. ([Senado Federal][17])
* **Regra chave:** Ideia legislativa vira Sugestão Legislativa quando atinge **20.000 apoios**. ([Senado Federal][18])

**Status atual de dados:**

* Não há documentação pública clara de uma **API oficial aberta** para ideias/apoios.
* Os dados são acessíveis via **HTML** (páginas de ideias, listas, etc.).

**Uso no Coral:**

* No MVP, o melhor é **não depender de scraping**:

  * Coral ajuda a pessoa a entender o processo e envia o **link + texto pronto** para ela registrar/acompanhar.
  * Opcional: futuramente, um “robô leitor” para verificar status de uma ideia específica (raspando HTML).

---

#### e-Democracia (Câmara)

* Portal da Câmara para participação em proposições (enquetes, debates). ([Portal da Câmara dos Deputados][19])
* Situação: em reestruturação em alguns momentos, sem API pública clara.

**Uso no Coral:**

* Igual e-Cidadania: **assistido, não integrado**:

  * Coral monta comentário técnico + linguagem simples.
  * Envia o passo a passo de como comentar naquela proposição na plataforma da Câmara.
  * Opcionalmente, registra internamente que o usuário **pretende comentar** aquele PL, pra acompanhar via dados da Câmara (não via e-Democracia em si).

---

### 2.7. Geodados e Demografia – IBGE

**API de dados agregados (SIDRA)** ([servicodados.ibge.gov.br][20])

* **Base:** `https://api.sidra.ibge.gov.br/` (vários endpoints, doc online).
* Permite puxar indicadores (população, renda, educação etc.) por município, região, etc.
* Retorna **JSON** (ou CSV, dependendo do endpoint/parâmetros).

**Malhas territoriais (shapefiles)** ([IBGE][21])

* Download de **malhas municipais**, distritos, setores censitários.
* Formato: **Shapefile/GeoJSON** dentro de ZIP.
* Usando IBGE, você consegue:

  * Mapear **bairros/regiões**.
  * Construir o **mapa de calor cívico** do Coral.
  * Relacionar seções eleitorais (via dados locais) com bairros.

**Uso no Coral:**

* Alimentar o **mapa de calor** por tema e `scope_level`.
* Enriquecer dossiês com contexto: população atingida, densidade etc.

---

### 2.8. Catálogos e agregadores – dados.gov.br e Base dos Dados

#### Portal Brasileiro de Dados Abertos (dados.gov.br)

* É o catálogo nacional de dados abertos. ([Dados Abertos][22])
* Tem **API própria** para listar datasets, organizações, temas. ([Serviços e Informações do Brasil][23])

**Formato:**

* API REST, retornando **JSON** com:

  * Conjuntos de dados (`/datasets`).
  * Temas, organizações etc.
* Precisa de **token** para uso mais intenso da API.

**Uso no Coral:**

* Descobrir rapidamente se existe dataset público sobre:

  * Ouvidoria municipal específica.
  * Dados abertos de um governo estadual ou prefeitura.

---

#### Base dos Dados

* Plataforma que hospeda dados já **tratados e prontos para análise** (SQL/BigQuery, Python, R). ([Base dos Dados][24])
* Tem datasets específicos para:

  * Dados da Câmara dos Deputados (proposições, deputados, votações).
  * Outros dados públicos brasileiros.

**Formato:**

* Você consulta via BigQuery (SQL) ou baixa como CSV.
* Os dados já vêm “limpos” e com chaves preparadas.

**Uso no Coral:**

* Em vez de bater na API da Câmara para fazer analytics pesados, você pode:

  * Usar o dataset da Câmara na Base dos Dados pra análises históricas, clusters, estatísticas.
  * Deixar a API da Câmara para **consulta em tempo real** (situação atual de um PL, por exemplo).

---

### 2.9. Legislativo Municipal/Estadual – Interlegis e Portais Modelo

**Portal Modelo / Interlegis** ([Portal Modelo][25])

* Muitas Câmaras Municipais usam um CMS padrão do Interlegis.
* Ele oferece uma **API simples em `/apidata`** que expõe conteúdos (inclusive alguns dados legislativos) em JSON.

**Uso no Coral:**

* Em cidades onde a Câmara usa Portal Modelo:

  * Dá pra consumir proposições locais, pautas, etc., diretamente do site da Câmara.
* Descoberta:

  * Ver se o domínio da Câmara tem `/transparencia/dados-abertos` ou `/apidata`.

---

## 3. Chaves de integração (como “amarrar” tudo isso no Coral)

Ao montar o “mapão” de dados do Coral, essas chaves são essenciais:

* **Código IBGE do município**

  * Usado pelo TSE (em vários datasets), IBGE, Querido Diário (`territory_id`) e muitos portais locais. ([docs.queridodiario.ok.org.br][12])
* **Código/Título do PL**

  * `siglaTipo + numero + ano` (Câmara/Senado) → dá pra resolver para um `id` usando as APIs.
* **CPF/CNPJ**

  * Para vincular contratos (Portal da Transparência, Querido Diário) a empresas e, eventualmente, cruzar com bancos de dados externos.
* **IDs de seção/zona eleitoral**

  * Do TSE, mapeados para bairros/regiões via IBGE + dados locais.
* **IDs internos do Coral**

  * `case_id`, `dossier_id`, `user_id_civico` → são a cola interna entre tudo isso e a camada blockchain.

---

## 4. Como isso encaixa nos agentes do Coral (visão bem prática)

### Agente Investigador – pipeline sugerido

1. **Recebe tema + local** do relato.
2. **Passos de dados:**

   * Legislativos:

     * Câmara (`/proposicoes`) e Senado/LexML pra achar PLs/leis relacionadas. ([dadosabertos.camara.leg.br][1])
   * Orçamento/contratos:

     * Portal da Transparência (despesas, contratos) pelo órgão + função + município. ([Portal da Transparência][7])
     * Querido Diário para atos municipais mais próximos. ([docs.queridodiario.ok.org.br][12])
   * Representatividade:

     * TSE – resultados por seção/município → “quem teve mais voto aqui”. ([Portal de Dados Abertos do TSE][5])
   * Contexto:

     * IBGE – população afetada, indicadores do município/setor. ([servicodados.ibge.gov.br][20])
3. **Output interno:**

   * Lista de “responsáveis prováveis” (órgão, secretaria, parlamentares).
   * Lista de PLs/leis/programas relacionados.
   * Dados de dinheiro/contrato vinculado.

### Agente Pedagogo

1. Recebe o PL/lei/ação e o perfil do usuário (bairro, problema).
2. Puxa o texto do PL (Câmara/Senado/LexML) em JSON/XML. ([dadosabertos.camara.leg.br][2])
3. Gera:

   * Metáforas.
   * Antes/Depois.
   * Impacto no bolso/rotina.
4. Se for PL monitorado por e-Cidadania, pode:

   * Adicionar info de consulta pública (estado, “sim/não”) com base em dados do Senado (quando disponíveis ou, no futuro, por scraping leve). ([Senado Federal][17])

### Gestor de Casos + Dossiês

* Usa tudo acima para:

  * Contar reclamações/apoios.
  * Montar relatórios com:

    * Mapas (IBGE + pontos do Coral).
    * Tabelas de gasto (Portal da Transparência).
    * Histórico de legislação (Câmara/Senado/LexML).
    * Dados de participação (Fala.BR agregado).

### Mapa de Calor Cívico

* Inputs:

  * Latitude/longitude ou endereço geocodificado de relatos.
  * Malhas IBGE (municípios/bairros/setores).
* Renderização:

  * Frontend com Leaflet/Mapbox usando shapes do IBGE. ([IBGE][21])

---

[1]: https://dadosabertos.camara.leg.br/swagger/api.html?utm_source=chatgpt.com "API de Dados Abertos da Câmara dos Deputados"
[2]: https://dadosabertos.camara.leg.br/?utm_source=chatgpt.com "Dados Abertos da Câmara dos Deputados"
[3]: https://www12.senado.leg.br/dados-abertos?utm_source=chatgpt.com "Dados Abertos"
[4]: https://www12.senado.leg.br/dados-abertos/conjuntos?grupo=legislacao&portal=legislativo&utm_source=chatgpt.com "Legislação - Dados Abertos"
[5]: https://dadosabertos.tse.jus.br/?utm_source=chatgpt.com "Portal de Dados Abertos do TSE: Bem vindo"
[6]: https://dadosabertos.tse.jus.br/dataset/resultados-2024?utm_source=chatgpt.com "Resultados - 2024 - Conjunto de dados"
[7]: https://portaldatransparencia.gov.br/api-de-dados?utm_source=chatgpt.com "API de Dados"
[8]: https://portaldatransparencia.gov.br/api-de-dados/cadastrar-email?utm_source=chatgpt.com "API de dados - Cadastro"
[9]: https://portaldatransparencia.gov.br/despesas?utm_source=chatgpt.com "Despesas Públicas"
[10]: https://www.tesourotransparente.gov.br/consultas/custos-api-de-dados-abertos?utm_source=chatgpt.com "Custos - API de Dados Abertos"
[11]: https://docs.queridodiario.ok.org.br/?utm_source=chatgpt.com "Querido Diário — documentação Querido Diário"
[12]: https://docs.queridodiario.ok.org.br/pt-br/latest/utilizando/api-publica.html?utm_source=chatgpt.com "API Pública — documentação Querido Diário"
[13]: https://api.queridodiario.ok.org.br/docs?utm_source=chatgpt.com "Querido Diário - Swagger UI"
[14]: https://falabr.cgu.gov.br/web/home?utm_source=chatgpt.com "Fala.BR - Plataforma Integrada de Ouvidoria e Acesso à ..."
[15]: https://dados.gov.br/dados/conjuntos-dados/falabr---modulo-acesso-a-informacao?utm_source=chatgpt.com "Fala.BR - Módulo Acesso à Informação"
[16]: https://falabr.cgu.gov.br/help?utm_source=chatgpt.com "Documentação da API do Fala.Br"
[17]: https://www12.senado.leg.br/ecidadania?utm_source=chatgpt.com "Portal e-Cidadania"
[18]: https://www12.senado.leg.br/ecidadania/principalideia?utm_source=chatgpt.com "Ideia Legislativa :: Portal e-Cidadania"
[19]: https://www2.camara.leg.br/atividade-legislativa/participe?utm_source=chatgpt.com "e-Democracia"
[20]: https://servicodados.ibge.gov.br/api/docs/agregados?versao=3&utm_source=chatgpt.com "API do IBGE"
[21]: https://www.ibge.gov.br/geociencias/organizacao-do-territorio/malhas-territoriais.html?utm_source=chatgpt.com "Malhas territoriais"
[22]: https://dados.gov.br/?utm_source=chatgpt.com "Portal de Dados Abertos"
[23]: https://www.gov.br/conecta/catalogo/apis/api-portal-de-dados-abertos?utm_source=chatgpt.com "API Portal de Dados Abertos — Catálogo de APIs ..."
[24]: https://basedosdados.org/dataset/3d388daa-2d20-49eb-8f55-6c561bef26b6?utm_source=chatgpt.com "Dados Abertos da Câmara dos Deputados"
[25]: https://portalmodelo.interlegis.leg.br/transparencia/dados-abertos?utm_source=chatgpt.com "Dados Abertos - Portal Modelo - Interlegis"
