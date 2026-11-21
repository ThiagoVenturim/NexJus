#!/usr/bin/env sh
# Instala as skills e agentes do NexJus no Claude Code sem precisar de pip.
# Uso: ./skills/install.sh [install|uninstall|validate|list] [--project DIR | --target DIR] [--force] [--dry-run]
# Sem argumentos instala em ~/.claude. Requer Python 3.11 ou mais novo.
set -eu

DIR="$(cd "$(dirname "$0")" && pwd)"
PYTHON="${PYTHON:-python3}"
if [ "$#" -eq 0 ]; then
  set -- install
fi
PYTHONPATH="$DIR/src${PYTHONPATH:+:$PYTHONPATH}" exec "$PYTHON" -m nexjus_skills "$@"
