---
name: doostudio
description: "Acessa CRM, leads, oportunidades e tarefas do DooStudio via MCP."
version: 1.0.0
platforms: [linux, macos, windows]
metadata:
  cadoo:
    tags: [doostudio, crm, leads, oportunidades, tarefas, pipeline, vendas, doo]
    related_skills: []
---

# DooStudio CRM

Esta skill conecta o Cadoo Agent ao CRM DooStudio via MCP server. Você tem acesso direto aos dados da sua empresa: contatos/leads, oportunidades de vendas, tarefas e pipelines.

## Configuração do MCP

Antes de usar, adicione o servidor MCP ao Cadoo (só precisa fazer uma vez):

```bash
cadoo mcp add doostudio --url https://doostudio.com.br/api/cadoo/mcp.php --auth header --header "User-Agent: CadooAgent/1.0"
```

O MCP usa automaticamente o mesmo JWT da sua autenticação `cadoo auth` — sem chave extra necessária.

## Ferramentas Disponíveis

| Ferramenta | O que faz |
|---|---|
| `doostudio_info_usuario` | Seu perfil + resumo do CRM (contagem de leads, oportunidades, tarefas) |
| `crm_contar_leads` | Conta total de leads/contatos, com filtro por status |
| `crm_listar_contatos` | Lista contatos com busca por nome, email ou telefone |
| `crm_listar_oportunidades` | Lista deals do pipeline, filtrando por status e estágio |
| `crm_listar_tarefas` | Lista tarefas abertas, filtrando por status |
| `crm_pipelines` | Mostra os pipelines configurados com seus estágios |
| `crm_criar_contato` | Cria novo contato/lead no CRM |
| `crm_criar_tarefa` | Cria nova tarefa no CRM |

## Workflow: Consultas ao CRM

Quando o usuário perguntar sobre leads, contatos, oportunidades ou tarefas:

1. Use `doostudio_info_usuario` primeiro se for uma pergunta geral ("como estou?", "resumo do CRM")
2. Use a ferramenta específica para perguntas focadas:
   - "quantos leads tenho?" → `crm_contar_leads`
   - "mostre meus contatos" → `crm_listar_contatos`
   - "quais oportunidades estão abertas?" → `crm_listar_oportunidades` com `status: "open"`
   - "tarefas pendentes" → `crm_listar_tarefas` com `status: "pending"`
   - "meus pipelines" → `crm_pipelines`

## Workflow: Criação de Registros

Quando o usuário pedir para criar algo:

**Criar contato/lead:**
```
crm_criar_contato({
  "name": "João Silva",
  "email": "joao@empresa.com",
  "phone": "(11) 99999-9999",
  "company": "Empresa Ltda",
  "notes": "Veio pelo Instagram"
})
```

**Criar tarefa:**
```
crm_criar_tarefa({
  "title": "Ligar para João Silva",
  "description": "Follow up da proposta enviada",
  "due_date": "2026-07-01",
  "priority": "high"
})
```

## Comportamento Esperado

- **Seja proativo**: após listar leads, ofereça criar uma tarefa de follow-up
- **Contextualize**: mostre totais antes de detalhar — "Você tem 79 leads. Os 5 mais recentes são..."
- **Paginação**: quando houver mais registros, informe e pergunte se quer ver mais
- **Números de negócio**: para oportunidades, destaque o valor total do pipeline
- **Idioma**: responda sempre no idioma do usuário (PT por padrão)

## Exemplos de Perguntas

- "Quantos leads eu tenho?"
- "Mostre meus contatos mais recentes"
- "Quais oportunidades estão em negociação?"
- "Tenho tarefas para hoje?"
- "Cria um lead para Maria Santos, email maria@teste.com"
- "Como está meu pipeline de vendas?"
- "Qual o resumo do meu CRM?"
