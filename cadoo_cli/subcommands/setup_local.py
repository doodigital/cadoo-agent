"""setup-local subcommand — install and configure a local Ollama model."""

from __future__ import annotations


def build_setup_local_parser(subparsers, *, cmd_setup_local) -> None:
    p = subparsers.add_parser(
        "setup-local",
        help="Configurar modelo local via Ollama (gratuito, sem internet depois)",
        description=(
            "Detecta o hardware, sugere o melhor modelo Ollama para sua máquina, "
            "baixa via 'ollama pull' e configura o Cadoo para usá-lo localmente."
        ),
    )
    p.add_argument(
        "--tier",
        choices=["basic", "intermediate", "robust"],
        help="Forçar um tier: basic (3B), intermediate (8B), robust (70B)",
    )
    p.add_argument(
        "--model",
        help="Forçar um modelo específico do Ollama (ex: mistral:7b)",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Mostrar o que seria feito sem executar nada",
    )
    p.set_defaults(func=cmd_setup_local)
