---
description: Faz uma auditoria de segurança completa do projeto FinFam, verificando isolamento de tenant, IDOR, CSRF, autenticação e validação de dados
disable-model-invocation: false
---

## Auditoria de Segurança — FinFam

Você é um auditor de segurança especializado em aplicações Flask com multi-tenancy. Analise todos os arquivos em `app/routes/` e `app/models.py` seguindo os passos abaixo.

### 1. Isolamento de Tenant (IDOR)
Para cada rota que lê, edita ou deleta um registro por ID, verifique se há filtro por `tenant_user_ids()` ou `tenant_users()` antes de agir. Exemplos de padrões inseguros:
- `Model.query.get_or_404(id)` sem verificar se o registro pertence ao tenant
- `filter_by(id=x)` sem `user_id.in_(uids)`

### 2. Autenticação e Sessão
- Todas as rotas protegidas estão na lista de `require_login` ou têm verificação própria?
- Rotas isentas (`exempt`) fazem sentido — alguma deveria ser protegida?
- A sessão armazena `tenant_id`? É usada consistentemente?

### 3. CSRF
- Todos os formulários POST incluem `{{ form.hidden_tag() }}` ou `csrf_token()`?
- Formulários em modais e deleções inline têm o token?

### 4. Validação de Entrada
- Campos numéricos (IDs vindos da URL) são validados como pertencentes ao tenant?
- Campos de texto têm `Length` e `DataRequired` onde necessário?
- O `user_id` passado como query param em filtros é validado contra `tenant_user_ids()`?

### 5. Exposição de Dados
- Algum endpoint da API (`/api/*`) retorna dados sem filtro de tenant?
- O endpoint `/auth/tenant-users` expõe mais dados do que deveria?

### Saída esperada

Gere um relatório no formato:

```
## Resultado da Auditoria de Segurança

### ✅ OK
- [lista de pontos seguros]

### ⚠️ Atenção (risco baixo / melhoria recomendada)
- [arquivo:linha] — descrição

### ❌ Vulnerabilidade (corrigir imediatamente)
- [arquivo:linha] — descrição + sugestão de fix

### Resumo
X pontos verificados | Y atenções | Z vulnerabilidades
```

Se encontrar vulnerabilidades, pergunte ao usuário se deseja corrigi-las agora antes de encerrar.
