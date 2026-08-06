from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from .app import JarvisAssistant
from .commands import CommandRouter
from .config import load_config
from .diagnostics import diagnostics_json, run_diagnostics, setup_local_models
from .logging_setup import configure_logging
from .single_instance import SingleInstance


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="JARVIS Local para Windows")
    parser.add_argument("--config", type=Path, help="Ruta alternativa de configuración")
    parser.add_argument("--diagnose", action="store_true", help="Verifica audio, voz, pantalla y Codex")
    parser.add_argument("--setup-models", action="store_true", help="Descarga los modelos locales gratuitos")
    parser.add_argument("--text", help="Prueba el enrutador con texto sin ejecutar acciones")
    parser.add_argument("--verbose", action="store_true", help="Activa registros detallados")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    config = load_config(args.config)
    configure_logging(config.logs_dir, args.verbose)

    if args.setup_models:
        for message in setup_local_models(config):
            print(message, flush=True)
        return 0

    if args.diagnose:
        checks = run_diagnostics(config)
        print(diagnostics_json(checks))
        return 0 if all(check.ok for check in checks) else 1

    if args.text is not None:
        decision = CommandRouter().handle(args.text)
        print(f"respuesta={decision.spoken}")
        print(f"accion={decision.action.name}")
        print(f"detalle={decision.payload}")
        return 0

    try:
        with SingleInstance():
            pid_path = config.data_dir / "jarvis.pid"
            pid_path.parent.mkdir(parents=True, exist_ok=True)
            pid_path.write_text(str(os.getpid()), encoding="ascii")
            try:
                JarvisAssistant(config).run()
            finally:
                if pid_path.exists() and pid_path.read_text(encoding="ascii").strip() == str(os.getpid()):
                    pid_path.unlink(missing_ok=True)
    except KeyboardInterrupt:
        return 0
    except RuntimeError as error:
        print(str(error), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
