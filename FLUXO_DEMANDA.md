# Fluxo de Criação de Demandas - Atualizado

## Visão Geral

O novo fluxo conversacional garante que:
1. O bot **confirma o entendimento** do problema antes de qualquer ação
2. O usuário pode **escolher se quer criar uma demanda** ou apenas conversar
3. Demandas similares são oferecidas **apenas após confirmação**

## Estados da Conversa

### 1. `confirming_problem`
**Quando:** Usuário relata um problema (classificação DEMANDA)

**Bot pergunta:**
```
📝 Deixa eu confirmar se entendi corretamente:

**[Título gerado pelo bot]**

[Descrição gerada pelo bot]

📍 Escopo: Nível X
📋 Tema: [tema]
🔹 Urgência: [urgência]

Entendi corretamente?

✅ Digite "sim" para confirmar
❌ Digite "não" para corrigir
```

**Próximo estado:**
- Se "sim" → `asking_create_demand`
- Se "não" → Estado limpo (usuário pode reformular)

---

### 2. `asking_create_demand`
**Quando:** Usuário confirmou que o bot entendeu o problema

**Bot pergunta:**
```
Ótimo! 👍

Agora você pode escolher:

1️⃣ Criar uma demanda - Sua solicitação será registrada e outros cidadãos poderão apoiá-la
2️⃣ Apenas conversar - Vou te ajudar sem criar um registro oficial

O que você prefere?

Digite "1" para criar a demanda
Digite "2" para apenas conversar
```

**Próximo estado:**
- Se "1" → Busca similares
  - Se encontrar similares → `choosing_similar_or_new`
  - Se não encontrar → Cria demanda automaticamente
- Se "2" → Estado limpo (modo conversação)

---

### 3. `choosing_similar_or_new`
**Quando:** Usuário escolheu criar demanda E existem demandas similares

**Bot pergunta:**
```
🔍 Encontrei demanda(s) similar(es) já criadas:

1. **[Título da demanda similar]**
   👥 [X] apoiadores | 📊 [Y]% similar

2. **[Outra demanda similar]**
   👥 [X] apoiadores | 📊 [Y]% similar

O que você prefere?

📌 Digite o número para apoiar uma demanda existente
🆕 Digite 'nova' para criar sua própria demanda
```

**Próximo estado:**
- Se número → Adiciona apoio e limpa estado
- Se "nova" → Cria nova demanda e limpa estado

---

## Diagrama de Fluxo

```
Usuário relata problema
        ↓
[Estado: confirming_problem]
"Entendi corretamente?"
        ↓
     Sim / Não
        ↓
    [Se Sim]
        ↓
[Estado: asking_create_demand]
"Criar demanda ou conversar?"
        ↓
   1 (criar) / 2 (conversar)
        ↓
  [Se 1 - criar]
        ↓
    Busca similares
        ↓
Encontrou? / Não encontrou
        ↓              ↓
    [Se Sim]      [Se Não]
        ↓              ↓
[choosing_similar_or_new]  Cria demanda
"Apoiar ou criar nova?"    automaticamente
        ↓
  número / "nova"
        ↓
Apoia / Cria nova
```

## Comparação: Antes vs Depois

### ANTES ❌
1. Usuário relata problema
2. Bot **CRIA DEMANDA IMEDIATAMENTE**
3. Bot mostra similares (mas já criou)
4. Usuário pode apoiar similar (mas já tem duplicata)

### DEPOIS ✅
1. Usuário relata problema
2. Bot **CONFIRMA ENTENDIMENTO**
3. Usuário confirma ou corrige
4. Bot **PERGUNTA SE QUER CRIAR DEMANDA**
5. Se sim → Busca similares → Oferece escolha
6. **Demanda só é criada após todas confirmações**

## Benefícios

✅ Evita criação de demandas duplicadas
✅ Usuário tem controle total do processo
✅ Confirmação reduz erros de interpretação
✅ Opção de não criar demanda (apenas conversar)
✅ Melhor UX conversacional
