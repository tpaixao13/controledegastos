#!/bin/bash
set -e

PROJECT_DIR="/home/finfam/Documents/Controledegastos"
VENV="$PROJECT_DIR/venv"

cd "$PROJECT_DIR"

git fetch origin

LOCAL=$(git rev-parse HEAD)
REMOTE=$(git rev-parse origin/main)

if [ "$LOCAL" = "$REMOTE" ]; then
    echo "Já está na versão mais recente."
    exit 0
fi

echo "Atualizando..."
git pull origin main

# Instala dependências novas se requirements.txt mudou
"$VENV/bin/pip" install -r requirements.txt -q

sudo systemctl restart finfam
echo "FinFam atualizado e reiniciado com sucesso."
