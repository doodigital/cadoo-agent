#!/usr/bin/env bash
# ============================================================================
# Cadoo Agent — Instalador oficial
# https://doost.online/cadoo-agent/install.sh
#
# Uso:
#   curl -fsSL https://doost.online/cadoo-agent/install.sh | bash
# ============================================================================
set -euo pipefail

REPO="https://github.com/doodigital/cadoo-agent.git"  # HTTPS para instalação pública
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

# ── Função: instalar pacote apt ─────────────────────────────────────────────
apt_install() {
  if command -v apt &>/dev/null; then
    info "Instalando $* via apt..."
    sudo apt-get update -qq && sudo apt-get install -y "$@" || error "Falha ao instalar $*. Tente manualmente: sudo apt install $*"
  else
    error "$* não encontrado e apt não está disponível. Instale manualmente."
  fi
}

# ── Verificar/instalar git ─────────────────────────────────────────────────
if ! command -v git &>/dev/null; then
  warn "git não encontrado."
  apt_install git
fi
success "git: $(git --version)"

# ── Verificar/instalar curl ────────────────────────────────────────────────
if ! command -v curl &>/dev/null; then
  warn "curl não encontrado."
  apt_install curl
fi

# ── Verificar/instalar Python 3.11+ ───────────────────────────────────────
PYTHON=""
for cmd in python3.13 python3.12 python3.11 python3; do
  if command -v "$cmd" &>/dev/null; then
    if "$cmd" -c 'import sys; exit(0 if sys.version_info >= (3,11) else 1)' 2>/dev/null; then
      PYTHON="$cmd"
      break
    fi
  fi
done

if [[ -z "$PYTHON" ]]; then
  warn "Python 3.11+ não encontrado."
  apt_install python3 python3-pip
  PYTHON="python3"
fi
success "Python: $($PYTHON --version)"

# ── Verificar/instalar venv + ensurepip ───────────────────────────────────
# Testa criando um venv real em tmp — é o único jeito confiável de checar
VENV_TEST=$(mktemp -d)
if ! "$PYTHON" -m venv "$VENV_TEST" &>/dev/null; then
  rm -rf "$VENV_TEST"
  warn "python venv/ensurepip não disponível."
  PY_VER=$("$PYTHON" -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
  apt_install "python${PY_VER}-venv"
  # Tentar novamente após instalar
  if ! "$PYTHON" -m venv "$VENV_TEST" &>/dev/null; then
    rm -rf "$VENV_TEST"
    error "Não foi possível instalar o módulo venv. Tente manualmente: sudo apt install python${PY_VER}-venv"
  fi
fi
rm -rf "$VENV_TEST"
success "venv: OK"

# ── Verificar/instalar pip ─────────────────────────────────────────────────
if ! "$PYTHON" -m pip --version &>/dev/null; then
  warn "pip não encontrado."
  apt_install python3-pip
fi
success "pip: OK"

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
rm -rf venv
"$PYTHON" -m venv venv --prompt cadoo

info "Instalando dependências (pode demorar alguns minutos)..."
venv/bin/pip install --quiet --upgrade pip
venv/bin/pip install --quiet -e ".[all]" || {
  warn "Instalação completa falhou, tentando versão básica..."
  venv/bin/pip install --quiet -e "."
}

# ── Criar comando cadoo ────────────────────────────────────────────────────
info "Instalando comando cadoo em $BIN_DIR..."

SHIM="$BIN_DIR/cadoo"
SHIM_CONTENT="#!/usr/bin/env bash
unset PYTHONPATH
unset PYTHONHOME
exec \"$INSTALL_DIR/venv/bin/cadoo\" \"\$@\""

if [[ -w "$BIN_DIR" ]]; then
  printf '%s\n' "$SHIM_CONTENT" > "$SHIM"
  chmod +x "$SHIM"
else
  printf '%s\n' "$SHIM_CONTENT" | sudo tee "$SHIM" > /dev/null
  sudo chmod +x "$SHIM"
fi

# ── Verificar ─────────────────────────────────────────────────────────────
echo ""
if [[ -x "$SHIM" ]]; then
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
  echo "  Execute: source ~/.bashrc"
  echo "  Ou adicione ao PATH: export PATH=\"$BIN_DIR:\$PATH\""
fi
