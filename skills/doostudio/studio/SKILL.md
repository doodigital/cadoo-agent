---
name: studio
description: "DooStudio: CRM completo, clientes, playbooks, planejamento e conteúdo via MCP."
version: 2.0.0
platforms: [linux, macos, windows]
metadata:
  cadoo:
    tags: [doostudio, studio, crm, leads, clientes, playbook, planejamento, conteudo, marketing, propostas, contratos, projetos, campanhas]
    related_skills: [doostudio]
---

# DooStudio — Agente Completo

Acesso total ao DooStudio via MCP: CRM (leads, pipeline, propostas, orçamentos, contratos, projetos, campanhas, tarefas) + Studio (clientes, playbooks, planejamento, conteúdo, posts, pautas).

## Setup Automático

Quando o MCP não estiver configurado, execute:

### Passo 1 — Verificar configuração

Leia `~/.cadoo/config.yaml` e verifique se existe `mcp_servers.doostudio` com `url` apontando para `doostudio.com.br/api/cadoo/mcp.php`.

Se já configurado com chave válida, pule para uso normal.

### Passo 2 — Solicitar API Key

> Para conectar ao DooStudio, preciso da sua API Key.
> Encontre em: **doostudio.com.br → Configurações → Integrações → API Keys**
>
> Cole sua chave aqui (formato: `doo_api_...`):

### Passo 3 — Configurar MCP

```bash
python3 -c "
import yaml, os
cfg_path = os.path.expanduser('~/.cadoo/config.yaml')
with open(cfg_path) as f:
    cfg = yaml.safe_load(f)
if 'mcp_servers' not in cfg:
    cfg['mcp_servers'] = {}
cfg['mcp_servers']['doostudio'] = {
    'enabled': True,
    'url': 'https://doostudio.com.br/api/cadoo/mcp.php',
    'headers': {
        'Authorization': 'Bearer API_KEY_AQUI',
        'User-Agent': 'CadooAgent/1.0 (cadoo-cli)'
    }
}
with open(cfg_path, 'w') as f:
    yaml.dump(cfg, f, allow_unicode=True, default_flow_style=False)
print('MCP configurado.')
"
```

### Passo 4 — Confirmar conexão

Chame `doostudio_info_usuario`. Se retornar o perfil, confirme e liste as opções disponíveis.

---

## Ferramentas Disponíveis (21 tools)

### Info
| Tool | O que faz |
|------|-----------|
| `doostudio_info_usuario` | Perfil do usuário autenticado + resumo geral |

### CRM — Leads e Contatos
| Tool | O que faz |
|------|-----------|
| `crm_listar_contatos` | Lista leads/contatos (626+) com busca por nome, email, telefone |
| `crm_contar_leads` | Conta total de leads, com filtro por status |

### CRM — Pipeline
| Tool | O que faz |
|------|-----------|
| `crm_listar_oportunidades` | Lista deals do pipeline com filtro por status e estágio |
| `crm_pipelines` | Lista os pipelines configurados com seus estágios |

### CRM — Negócios
| Tool | O que faz |
|------|-----------|
| `crm_listar_propostas` | Lista propostas comerciais (41) |
| `crm_listar_orcamentos` | Lista orçamentos (28) |
| `crm_listar_contratos` | Lista contratos (26) |

### CRM — Operação
| Tool | O que faz |
|------|-----------|
| `crm_listar_tarefas` | Lista tarefas (95) com filtro por status |
| `crm_listar_projetos` | Lista projetos (8) |
| `crm_listar_campanhas` | Lista campanhas (8) |

### CRM — Escrita
| Tool | O que faz |
|------|-----------|
| `crm_criar_contato` | Cria novo lead/contato |
| `crm_criar_tarefa` | Cria nova tarefa |

### Studio — Clientes
| Tool | O que faz |
|------|-----------|
| `studio_listar_clientes` | Lista clientes de marketing com gestor ativo |
| `studio_playbook_get` | Playbook completo: identidade, voz, personas, UVP, redes |

### Studio — Planejamento e Conteúdo
| Tool | O que faz |
|------|-----------|
| `studio_planning_monthly` | Planejamento do mês por cliente, agrupado por status |
| `studio_content_list` | Lista conteúdos com filtros: cliente, status, data |
| `studio_content_create` | Cria conteúdo no calendário editorial |
| `studio_content_update` | Atualiza campos de um conteúdo existente |

### Studio — Social
| Tool | O que faz |
|------|-----------|
| `studio_listar_posts` | Lista posts publicados ou agendados |
| `studio_listar_pautas` | Lista pautas de conteúdo |

---

## Workflows

### "Como está meu CRM?"
1. `doostudio_info_usuario` — resumo geral
2. Destaque: total de leads, oportunidades abertas, tarefas pendentes, propostas em andamento

### "Mostre meu pipeline"
1. `crm_pipelines` — ver estágios
2. `crm_listar_oportunidades(status="open")` — deals ativos com valor

### "Planejamento de conteúdo de julho"
1. `studio_listar_clientes` — obter IDs
2. `studio_planning_monthly(client_id=X, month="2026-07")` por cliente
3. Apresentar agrupado por status

### "Crie conteúdo para o cliente X"
1. `studio_listar_clientes` — obter client_id
2. `studio_playbook_get(client_id=X)` — consultar tom de voz e diretrizes
3. `studio_content_create(...)` com os dados

### "Tenho propostas abertas?"
1. `crm_listar_propostas` — listar com status/valor
2. Destacar valor total do pipeline comercial

---

## Comportamento

- **Proativo**: após listar leads, ofereça criar tarefa de follow-up; após listar clientes, ofereça ver planejamento
- **Contextual**: ao criar conteúdo, sempre consulte o playbook primeiro
- **Números reais**: leads vêm de `crm_customers` (626+), não de perfis comportamentais
- **Paginação**: quando houver mais registros, informe e pergunte se quer ver mais
- **Idioma**: português por padrão
- **Erros 401/403**: API Key pode ter expirado — execute o setup novamente
