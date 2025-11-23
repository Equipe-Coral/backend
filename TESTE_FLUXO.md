# Teste do Novo Fluxo de Criação de Demandas

## Cenário 1: Fluxo completo - Criar nova demanda

### Passo 1: Usuário relata problema
**Entrada:** "Tem um cachorro morto na rua que precisa ser coletado"

**Estado criado:** `confirming_problem`

**Resposta esperada:**
```
📝 Deixa eu confirmar se entendi corretamente:

**Remoção de Animal Morto na Via Pública**

Há um cachorro morto na rua que precisa ser coletado...

📍 Escopo: Nível 1
📋 Tema: Meio Ambiente
🔹 Urgência: Media

Entendi corretamente?

✅ Digite "sim" para confirmar
❌ Digite "não" para corrigir
```

---

### Passo 2: Usuário confirma
**Entrada:** "sim"

**Estado atualizado:** `asking_create_demand`

**Resposta esperada:**
```
Ótimo! 👍

Agora você pode escolher:

1️⃣ Criar uma demanda - Sua solicitação será registrada e outros cidadãos poderão apoiá-la
2️⃣ Apenas conversar - Vou te ajudar sem criar um registro oficial

O que você prefere?

Digite "1" para criar a demanda
Digite "2" para apenas conversar
```

---

### Passo 3a: Usuário escolhe criar demanda
**Entrada:** "1"

**Sistema:** Gera embedding e busca demandas similares

#### Se encontrar similares:
**Estado atualizado:** `choosing_similar_or_new`

**Resposta esperada:**
```
🔍 Encontrei demanda(s) similar(es) já criadas:

1. **Coleta de Animal Morto na Rua**
   👥 5 apoiadores | 📊 85% similar

O que você prefere?

📌 Digite o número para apoiar uma demanda existente
🆕 Digite 'nova' para criar sua própria demanda
```

#### Se NÃO encontrar similares:
**Estado:** Limpo

**Resposta esperada:**
```
✅ Demanda criada com sucesso!

**Remoção de Animal Morto na Via Pública**

📍 Escopo: Nível 1
📋 Tema: Meio Ambiente
🔹 Urgência: Media
👥 Apoiadores: 1 (você)

[Link da demanda]

💡 Compartilhe para aumentar a pressão!
```

---

### Passo 3b: Usuário escolhe apenas conversar
**Entrada:** "2"

**Estado:** Limpo

**Resposta esperada:**
```
Entendido! 😊

Estou aqui para te ajudar. Você pode:

💬 Tirar dúvidas sobre leis e direitos
📍 Pedir orientações sobre serviços públicos
🤝 Conversar sobre questões da sua comunidade

Como posso te ajudar?
```

---

### Passo 4 (se encontrou similares): Escolha final
**Entrada opção 1:** "1" (apoiar similar)

**Resposta esperada:**
```
✅ Você agora apoia esta demanda!

**Coleta de Animal Morto na Rua**

👥 Total de apoiadores: 6

💪 Quanto mais gente apoiar, maior a pressão!
```

**Entrada opção 2:** "nova" (criar nova mesmo assim)

**Resposta esperada:**
```
✅ Nova demanda criada!

**Remoção de Animal Morto na Via Pública**

📍 Escopo: Nível 1
👥 Apoiadores: 1 (você)

[Link da demanda]
```

---

## Cenário 2: Usuário não confirma entendimento

### Passo 1: Usuário relata problema
**Entrada:** "Tem um cachorro morto na rua"

**Resposta:** [Mensagem de confirmação como acima]

---

### Passo 2: Usuário discorda
**Entrada:** "não"

**Estado:** Limpo

**Resposta esperada:**
```
Sem problemas! 😊

Por favor, me conte novamente qual é o problema, com mais detalhes:

💡 Dica: Seja específico sobre:
- O que está acontecendo
- Onde está acontecendo
- Qual a urgência
```

---

## Variações de Entrada Aceitas

### Confirmação Positiva (Passo 2):
- "sim", "s", "yes", "y"
- "correto", "exato", "isso"
- "ok", "okay", "certo"
- "perfeito", "pode"
- "confirmo", "entendeu"
- "uhum", "ahan", "aham"

### Confirmação Negativa (Passo 2):
- "não", "nao", "n", "no"
- "errado", "incorreto"
- "negativo"

### Criar Demanda (Passo 3):
- "1", "criar", "demanda", "criar demanda"

### Apenas Conversar (Passo 3):
- "2", "conversar", "apenas conversar"

### Apoiar Similar (Passo 4):
- Qualquer número ("1", "2", "3")

### Criar Nova (Passo 4):
- "nova", "criar"

---

## Pontos Críticos para Testar

✅ **Prioridade de Estados:** Estados de conversa devem ser verificados ANTES da classificação
✅ **Não criar demanda prematuramente:** Demanda só deve ser criada após TODAS as confirmações
✅ **Persistência de dados:** Contexto deve ser mantido entre mensagens
✅ **Limpeza de estado:** Estado deve ser limpo após conclusão do fluxo
✅ **Reconhecimento flexível:** Aceitar variações naturais de resposta
