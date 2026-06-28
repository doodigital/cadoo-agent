"""Local model setup via Ollama — hardware detection, tier selection, pull, config."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from typing import Any, Dict, Optional, Tuple

from cadoo_cli.cli_output import print_error, print_info, print_success, print_warning


# ---------------------------------------------------------------------------
# Tier definitions
# ---------------------------------------------------------------------------

_TIERS: Dict[str, Dict[str, Any]] = {
    "basic": {
        "label": "Básico",
        "model": "llama3.2:3b",
        "size_gb": 2.0,
        "description": "Llama 3.2 3B — rápido, leve, funciona em qualquer máquina",
        "min_ram_gb": 4,
    },
    "intermediate": {
        "label": "Intermediário",
        "model": "llama3.1:8b",
        "size_gb": 5.0,
        "description": "Llama 3.1 8B — bom equilíbrio entre qualidade e velocidade",
        "min_ram_gb": 10,
    },
    "robust": {
        "label": "Robusto",
        "model": "llama3.3:70b-q4_K_M",
        "size_gb": 43.0,
        "description": "Llama 3.3 70B Q4 — máxima qualidade, requer GPU ou RAM ≥ 48 GB",
        "min_ram_gb": 48,
    },
}

OLLAMA_BASE_URL = "http://localhost:11434/v1"


# ---------------------------------------------------------------------------
# Hardware detection
# ---------------------------------------------------------------------------

def _ram_gb() -> float:
    """Return total system RAM in GB."""
    try:
        import psutil
        return psutil.virtual_memory().total / (1024 ** 3)
    except Exception:
        pass
    # Fallback: /proc/meminfo (Linux)
    try:
        with open("/proc/meminfo") as f:
            for line in f:
                if line.startswith("MemTotal:"):
                    kb = int(line.split()[1])
                    return kb / (1024 ** 2)
    except Exception:
        pass
    # Fallback: sysctl (macOS)
    try:
        out = subprocess.check_output(["sysctl", "-n", "hw.memsize"], text=True, timeout=3)
        return int(out.strip()) / (1024 ** 3)
    except Exception:
        pass
    return 0.0


def _nvidia_vram_gb() -> Optional[float]:
    """Return NVIDIA GPU VRAM in GB, or None if not available."""
    if not shutil.which("nvidia-smi"):
        return None
    try:
        out = subprocess.check_output(
            ["nvidia-smi", "--query-gpu=memory.total", "--format=csv,noheader,nounits"],
            text=True, timeout=5,
        )
        total_mb = sum(int(line.strip()) for line in out.strip().splitlines() if line.strip().isdigit())
        return total_mb / 1024 if total_mb > 0 else None
    except Exception:
        return None


def _apple_vram_gb() -> Optional[float]:
    """Return Apple Silicon unified memory in GB (same pool as RAM), or None."""
    if sys.platform != "darwin":
        return None
    try:
        out = subprocess.check_output(
            ["system_profiler", "SPHardwareDataType"],
            text=True, timeout=5,
        )
        for line in out.splitlines():
            if "Memory:" in line or "Chip:" in line:
                if "Apple" in line or "M1" in line or "M2" in line or "M3" in line or "M4" in line:
                    return _ram_gb()  # unified memory
        return None
    except Exception:
        return None


def detect_hardware() -> Dict[str, Any]:
    """Detect RAM and GPU specs. Returns dict with ram_gb, gpu_vram_gb, gpu_type."""
    ram = _ram_gb()
    nvidia = _nvidia_vram_gb()
    apple = _apple_vram_gb()

    if nvidia is not None:
        return {"ram_gb": ram, "gpu_vram_gb": nvidia, "gpu_type": "nvidia"}
    if apple is not None:
        return {"ram_gb": ram, "gpu_vram_gb": apple, "gpu_type": "apple"}
    return {"ram_gb": ram, "gpu_vram_gb": None, "gpu_type": "none"}


# ---------------------------------------------------------------------------
# Tier suggestion
# ---------------------------------------------------------------------------

def suggest_tier(hw: Dict[str, Any]) -> str:
    """Return the recommended tier key given hardware specs."""
    ram = hw.get("ram_gb", 0)
    vram = hw.get("gpu_vram_gb") or 0
    gpu_type = hw.get("gpu_type", "none")

    effective = max(ram, vram) if gpu_type != "none" else ram

    if effective >= 48:
        return "robust"
    if effective >= 10:
        return "intermediate"
    return "basic"


# ---------------------------------------------------------------------------
# Ollama checks
# ---------------------------------------------------------------------------

def check_ollama_installed() -> bool:
    return shutil.which("ollama") is not None


def check_model_exists(model: str) -> bool:
    """Return True if the model is already pulled locally."""
    try:
        result = subprocess.run(
            ["ollama", "list"],
            capture_output=True, text=True, timeout=5,
        )
        model_base = model.split(":")[0]
        return model_base in result.stdout or model in result.stdout
    except Exception:
        return False


def pull_model(model: str) -> bool:
    """Run ollama pull with live output. Returns True on success."""
    try:
        result = subprocess.run(["ollama", "pull", model])
        return result.returncode == 0
    except KeyboardInterrupt:
        print()
        print_warning("Download interrompido.")
        return False
    except Exception as exc:
        print_error(f"Erro ao executar ollama pull: {exc}")
        return False


# ---------------------------------------------------------------------------
# Config persistence
# ---------------------------------------------------------------------------

def write_ollama_config(model: str) -> None:
    from cadoo_cli.config import load_config, save_config
    config = load_config()
    if "model" not in config or not isinstance(config.get("model"), dict):
        config["model"] = {}
    config["model"]["provider"] = "custom"
    config["model"]["default"] = model
    config["model"]["base_url"] = OLLAMA_BASE_URL
    save_config(config)


# ---------------------------------------------------------------------------
# Main flow
# ---------------------------------------------------------------------------

def _print_hardware(hw: Dict[str, Any]) -> None:
    ram = hw["ram_gb"]
    gpu_type = hw["gpu_type"]
    vram = hw.get("gpu_vram_gb")

    ram_str = f"{ram:.1f} GB RAM"
    if gpu_type == "nvidia" and vram:
        gpu_str = f"  GPU NVIDIA: {vram:.1f} GB VRAM"
    elif gpu_type == "apple":
        gpu_str = "  GPU: Apple Silicon (memória unificada)"
    else:
        gpu_str = "  GPU: não detectada"

    print_info(f"  RAM: {ram_str}")
    print_info(gpu_str)


def _print_tier_table() -> None:
    print()
    print_info("  Tiers disponíveis:")
    for key, t in _TIERS.items():
        print_info(f"    [{key}]  {t['label']:14s}  {t['model']:30s}  ~{t['size_gb']:.0f} GB")
    print()


def run_local_setup(args) -> None:
    from cadoo_cli.cli_output import prompt_yes_no
    from cadoo_cli.setup import prompt_choice  # prompt_choice lives in setup.py

    dry_run: bool = getattr(args, "dry_run", False)
    forced_tier: Optional[str] = getattr(args, "tier", None)
    forced_model: Optional[str] = getattr(args, "model", None)

    print()
    print("◆ Configuração de Modelo Local (Ollama)")
    print()

    # --- hardware ---
    print_info("Detectando hardware...")
    hw = detect_hardware()
    _print_hardware(hw)
    print()

    # --- model selection ---
    if forced_model:
        model = forced_model
        tier_key = forced_tier or "basic"
        tier = _TIERS.get(tier_key, _TIERS["basic"])
        tier["model"] = model
    elif forced_tier:
        tier_key = forced_tier
        tier = _TIERS[tier_key]
        model = tier["model"]
    else:
        tier_key = suggest_tier(hw)
        tier = _TIERS[tier_key]
        model = tier["model"]
        print_info(f"Recomendado para seu hardware:  [{tier_key}]  {tier['description']}")
        print_info(f"  Modelo: {model}  (~{tier['size_gb']:.0f} GB)")
        print()

        if not dry_run:
            use_recommended = prompt_yes_no("Usar este modelo?", default=True)
            if not use_recommended:
                _print_tier_table()
                tier_names = list(_TIERS.keys())
                tier_labels = [f"{_TIERS[k]['label']} — {_TIERS[k]['model']}" for k in tier_names]
                idx = prompt_choice("Escolha o tier:", tier_labels, default=tier_names.index(tier_key))
                tier_key = tier_names[idx]
                tier = _TIERS[tier_key]
                model = tier["model"]

    print_info(f"Modelo selecionado: {model}")
    print()

    if dry_run:
        print_info("[dry-run] Nenhuma alteração será feita.")
        print_info(f"[dry-run] Executaria: ollama pull {model}")
        print_info(f"[dry-run] Config: provider=custom, base_url={OLLAMA_BASE_URL}, default={model}")
        return

    # --- check ollama ---
    if not check_ollama_installed():
        print_error("Ollama não está instalado.")
        print()
        print_info("Instale em: https://ollama.com/download")
        print()
        if sys.platform == "linux":
            print_info("  Linux (uma linha):")
            print_info("    curl -fsSL https://ollama.com/install.sh | sh")
        elif sys.platform == "darwin":
            print_info("  macOS:")
            print_info("    brew install ollama")
            print_info("  ou baixe o app em https://ollama.com/download")
        elif sys.platform.startswith("win"):
            print_info("  Windows: baixe o instalador em https://ollama.com/download")
        print()
        print_info("Após instalar, execute novamente: cadoo setup-local")
        sys.exit(1)

    # --- pull ---
    if check_model_exists(model):
        print_success(f"Modelo {model} já está instalado. Pulando download.")
    else:
        disk_needed = tier.get("size_gb", 5.0)
        print_info(f"Baixando {model} (~{disk_needed:.0f} GB). Isso pode demorar alguns minutos...")
        print()
        ok = pull_model(model)
        if not ok:
            print_error(f"Falha ao baixar {model}.")
            print_info("Verifique sua conexão e tente novamente: cadoo setup-local")
            sys.exit(1)

    print()

    # --- config ---
    write_ollama_config(model)

    print_success(f"Pronto! Cadoo configurado para usar {model} localmente.")
    print()
    print_info(f"  Provider: Ollama local ({OLLAMA_BASE_URL})")
    print_info(f"  Modelo:   {model}")
    print()
    print_info("Inicie com: cadoo")
    print_info("Para voltar ao Groq ou outro provider: cadoo model")
    print()
