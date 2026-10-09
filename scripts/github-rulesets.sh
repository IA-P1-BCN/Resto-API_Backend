#!/bin/sh
# Bloquea el merge en dev y main si el CI no está en verde (HU-16).
#
# Crea (o actualiza) en los dos repos un ruleset "CI obligatorio" que exige el check del CI:
#   - Resto-API_Backend  → job "tests" de ci.yml
#   - Resto-API_Frontend → job "build" de ci.yml
# No toca la protección de ramas que ya existe (aprobaciones, main solo para Anna).
#
# Requisitos: gh autenticado con permisos de admin en la organización.
#   sh scripts/github-rulesets.sh
set -e

ORG=IA-P1-BCN
NAME="CI obligatorio"
GITHUB_ACTIONS_APP_ID=15368

aplicar() {
  repo=$1
  check=$2
  body=$(cat <<EOF
{
  "name": "$NAME",
  "target": "branch",
  "enforcement": "active",
  "conditions": {"ref_name": {"include": ["refs/heads/dev", "refs/heads/main"], "exclude": []}},
  "rules": [{
    "type": "required_status_checks",
    "parameters": {
      "strict_required_status_checks_policy": false,
      "required_status_checks": [{"context": "$check", "integration_id": $GITHUB_ACTIONS_APP_ID}]
    }
  }]
}
EOF
)
  id=$(gh api "repos/$ORG/$repo/rulesets" --jq ".[] | select(.name == \"$NAME\") | .id")
  if [ -n "$id" ]; then
    echo "$body" | gh api -X PUT "repos/$ORG/$repo/rulesets/$id" --input - > /dev/null
    echo "$repo: ruleset actualizado (check \"$check\" obligatorio en dev y main)"
  else
    echo "$body" | gh api -X POST "repos/$ORG/$repo/rulesets" --input - > /dev/null
    echo "$repo: ruleset creado (check \"$check\" obligatorio en dev y main)"
  fi
}

aplicar Resto-API_Backend tests
aplicar Resto-API_Frontend build
