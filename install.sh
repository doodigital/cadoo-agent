#!/usr/bin/env bash
# ============================================================================
# Cadoo Agent — Instalador oficial
# https://doost.online/cadoo-agent/install.sh
#
# Uso:
#   curl -fsSL https://doost.online/cadoo-agent/install.sh | bash
# ============================================================================
set -euo pipefail

REPO="https://github.com/doodigital/cadoo-agent.git"
INSTALL_DIR="$HOME/.cadoo-agent"
BIN_DIR="/usr/local/bin"

# ── Cores ──────────────────────────────────────────────────────────────────
PURPLE='\033[0;35m'
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

info()    { echo -e "${PURPLE}[cadoo]${NC} $*"; }
success() { echo -e "${GREEN}[cadoo]${NC} $*"; }
warn()    { echo -e "${YELLOW}[cadoo]${NC} $*"; }
error()   { echo -e "${RED}[cadoo] ERRO:${NC} $*"; exit 1; }

# ── Banner ─────────────────────────────────────────────────────────────────
echo ""
echo -e "${PURPLE}"
echo "  ██████╗ █████╗ ██████╗  ██████╗  ██████╗ "
echo " ██╔════╝██╔══██╗██╔══██╗██╔═══██╗██╔═══██╗"
echo " ██║     ███████║██║  ██║██║   ██║██║   ██║"
echo " ██║     ██╔══██║██║  ██║██║   ██║██║   ██║"
echo " ╚██████╗██║  ██║██████╔╝╚██████╔╝╚██████╔╝"
echo "  ╚═════╝╚═╝  ╚═╝╚═════╝  ╚═════╝  ╚═════╝"
echo -e "${NC}"
echo -e "  ${PURPLE}Cadoo Agent${NC} — por DooStudio"
echo -e "  ${PURPLE}https://doostudio.com.br${NC}"
echo ""

# ── Sistema ────────────────────────────────────────────────────────────────
OS="$(uname -s)"
if [[ "$OS" != "Linux" && "$OS" != "Darwin" ]]; then
  error "Sistema não suportado: $OS. Use Linux ou macOS."
fi

# ── Dependências ───────────────────────────────────────────────────────────
info "Verificando dependências..."

# Python 3.11+
PYTHON=""
for cmd in python3.13 python3.12 python3.11 python3; do
  if command -v "$cmd" &>/dev/null; then
    version=$("$cmd" -c 'import sys; print(sys.version_info[:2])')
    if "$cmd" -c 'import sys; exit(0 if sys.version_info >= (3,11) else 1)' 2>/dev/null; then
      PYTHON="$cmd"
      break
    fi
  fi
done

if [[ -z "$PYTHON" ]]; then
  error "Python 3.11+ não encontrado. Instale com: sudo apt install python3 (Linux) ou brew install python (Mac)"
fi
success "Python: $($PYTHON --version)"

# git
if ! command -v git &>/dev/null; then
  error "git não encontrado. Instale com: sudo apt install git"
fi
success "git: $(git --version)"

# pip / venv
if ! "$PYTHON" -m venv --help &>/dev/null; then
  warn "Módulo venv não encontrado."
  info "Tentando instalar python3-venv..."
  if command -v apt &>/dev/null; then
    PY_VER=$("$PYTHON" -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
    sudo apt install -y "python${PY_VER}-venv" || error "Falha ao instalar python-venv. Tente manualmente: sudo apt install python3-venv"
  else
    error "Instale o módulo venv manualmente para seu sistema."
  fi
fi

# ── Clonar ou atualizar ────────────────────────────────────────────────────
if [[ -d "$INSTALL_DIR/.git" ]]; then
  info "Atualizando instalação existente em $INSTALL_DIR..."
  git -C "$INSTALL_DIR" pull --ff-only
else
  info "Clonando repositório em $INSTALL_DIR..."
  git clone --depth=1 "$REPO" "$INSTALL_DIR"
fi

cd "$INSTALL_DIR"

# ── Ambiente virtual ───────────────────────────────────────────────────────
info "Criando ambiente virtual..."
"$PYTHON" -m venv venv --prompt cadoo

info "Instalando dependências (pode demorar alguns minutos)..."
venv/bin/pip install --quiet --upgrade pip
venv/bin/pip install --quiet -e ".[all]" || venv/bin/pip install --quiet -e "."

# ── Criar comando cadoo ────────────────────────────────────────────────────
info "Instalando comando cadoo em $BIN_DIR..."

SHIM="$BIN_DIR/cadoo"
SHIM_CONTENT="#!/usr/bin/env bash
unset PYTHONPATH
unset PYTHONHOME
exec \"$INSTALL_DIR/venv/bin/cadoo\" \"\$@\""

if [[ -w "$BIN_DIR" ]]; then
  echo "$SHIM_CONTENT" > "$SHIM"
  chmod +x "$SHIM"
else
  echo "$SHIM_CONTENT" | sudo tee "$SHIM" > /dev/null
  sudo chmod +x "$SHIM"
fi

# ── Verificar ─────────────────────────────────────────────────────────────
if command -v cadoo &>/dev/null || [[ -x "$SHIM" ]]; then
  echo ""
  success "✓ Cadoo Agent instalado com sucesso!"
  echo ""
  echo -e "  Execute ${PURPLE}cadoo setup${NC} para configurar."
  echo -e "  Execute ${PURPLE}cadoo${NC} para iniciar o agente."
  echo ""
  echo -e "  Blog: ${PURPLE}https://leadmestre.com${NC}"
  echo -e "  Site: ${PURPLE}https://doostudio.com.br${NC}"
  echo ""
else
  warn "Instalado, mas 'cadoo' pode não estar no PATH desta sessão."
  echo "  Adicione ao seu shell: export PATH=\"$BIN_DIR:\$PATH\""
fi
