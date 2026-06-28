---
name: studio
description: "DooStudio: clientes, playbooks, planejamento e conteúdo via MCP."
version: 1.0.0
platforms: [linux, macos, windows]
metadata:
  cadoo:
    tags: [doostudio, studio, clientes, playbook, planejamento, conteudo, marketing, doo]
    related_skills: [doostudio]
---

# DooStudio — Agente de Marketing

Esta skill conecta o Cadoo ao DooStudio via MCP, dando acesso a clientes, playbooks, planejamento de conteúdo e calendário editorial.

## Setup Automático

Quando o usuário invocar `/studio` pela primeira vez (ou quando o MCP não estiver configurado), execute este fluxo:

### Passo 1 — Verificar se o MCP já está configurado

Use a ferramenta `read_file` para ler `~/.cadoo/config.yaml` e verificar se existe uma entrada `mcp_servers.doostudio` com `url` apontando para `doostudio.com.br/api/cadoo/mcp.php`.

Se já estiver configurado e com chave válida, pule direto para o uso normal.

### Passo 2 — Solicitar a API Key (se não configurado)

Peça ao usuário:

> Para conectar ao DooStudio, preciso da sua API Key.
> Você encontra em: **doostudio.com.br → Configurações → Integrações → API Keys**
> 
> Cole sua chave aqui (formato: `doo_api_...`):

### Passo 3 — Configurar o MCP automaticamente

Após receber a chave, use a ferramenta `terminal` para adicionar o MCP ao config:

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
print('MCP configurado com sucesso.')
"
```

Substitua `API_KEY_AQUI` pela chave fornecida pelo usuário.

### Passo 4 — Confirmar a conexão

Após configurar, teste chamando a tool `studio_listar_clientes`. Se retornar a lista, confirme:

> ✓ Conectado ao DooStudio! Encontrei X clientes. 
> O que você gostaria de fazer?

Se der erro de autenticação, informe que a chave pode estar incorreta e peça novamente.

---

## Ferramentas Disponíveis

### Clientes
| Tool | O que faz |
|------|-----------|
| `studio_listar_clientes` | Lista todos os clientes de marketing com gestor ativo |

### Playbook
| Tool | O que faz |
|------|-----------|
| `studio_playbook_get` | Retorna o playbook completo: identidade visual, voz, personas, UVP, redes sociais |

### Planejamento
| Tool | O que faz |
|------|-----------|
| `studio_planning_monthly` | Lista o planejamento do mês por cliente, agrupado por status |

### Conteúdo
| Tool | O que faz |
|------|-----------|
| `studio_content_list` | Lista conteúdos com filtros: cliente, status, data |
| `studio_content_create` | Cria novo conteúdo no calendário editorial |
| `studio_content_update` | Atualiza campos de um conteúdo existente |

### CRM (também disponível)
| Tool | O que faz |
|------|-----------|
| `crm_listar_contatos` | Lista leads/contatos com busca |
| `crm_listar_oportunidades` | Lista deals do pipeline |
| `crm_listar_tarefas` | Lista tarefas por status |
| `crm_criar_contato` | Cria novo lead |
| `crm_criar_tarefa` | Cria nova tarefa |
| `doostudio_info_usuario` | Perfil do usuário autenticado |

---

## Workflows

### "Mostre meu planejamento de julho"
1. Liste os clientes: `studio_listar_clientes`
2. Para cada cliente relevante (ou o mencionado): `studio_planning_monthly(client_id=X, month="2026-07")`
3. Apresente agrupado por status (aprovado, em criação, publicado, etc.)

### "Crie um conteúdo para o cliente X"
1. Se não souber o client_id: `studio_listar_clientes` primeiro
2. Consulte o playbook: `studio_playbook_get(client_id=X)` para tom de voz e diretrizes
3. Crie: `studio_content_create` com os dados fornecidos

### "Qual é o playbook do cliente Y?"
1. Liste clientes para obter o ID: `studio_listar_clientes`
2. `studio_playbook_get(client_id=ID)` — retorna identidade visual, voz, personas, UVP

### "Edite o conteúdo #123"
1. Liste para confirmar: `studio_content_list(client_id=X, status="draft")`
2. `studio_content_update(content_id=123, fields={...})`

---

## Comportamento

- **Proativo**: após listar clientes, ofereça ver o planejamento do mês atual
- **Contextual**: ao criar conteúdo, sempre consulte o playbook primeiro para respeitar o tom de voz
- **Idioma**: responda em português por padrão
- **Erros de auth**: se qualquer tool retornar 401/403, informe que a API Key pode ter expirado e execute o setup novamente
