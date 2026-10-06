#!/usr/bin/env bash
# Regressão do launcher `plexo context`.
#
# Os 4 bugs abaixo vieram do commit cc78b48, escrito por um subagente que
# morreu antes de revisar o proprio trabalho. bash -n so valida sintaxe, entao
# cada um foi reproduzido de verdade antes de corrigir.
#
# SEGURANCA (Regra 0, AGENTS.md — 2026-10-06):
#   Nunca reatribuir $HOME num teste nem apagar o home real. Cada cenario usa
#   TMPDIR_TESTE="$(mktemp -d)" numa variavel PROPIA; o HOME fake so existe no
#   ambiente do processo filho (prefixo de atribuicao no comando), nunca no
#   shell do script. Antes de qualquer rm, valida-se que a variavel e nao-vazia
#   e diferente de "/". Ver contexto do wipe em ~/.config/opencode/AGENTS.md.
set -uo pipefail

REPO="$(cd "$(dirname "$0")/.." && pwd)"
LAUNCHER="$REPO/plexo"
PASS=0
FAIL=0
unset TMPDIR_TESTE

ok()   { printf '  \033[32mok\033[0m   %s\n' "$1"; PASS=$((PASS+1)); }
bad()  { printf '  \033[31mFAIL\033[0m %s\n' "$1"; FAIL=$((FAIL+1)); }

# Sobe um HOME fake para um cenario. Grava TMPDIR_TESTE (nunca HOME).
fake_home() {
  TMPDIR_TESTE="$(mktemp -d)" || { echo "mktemp falhou"; exit 1; }
  mkdir -p "$TMPDIR_TESTE/.plexo"
}

# Remove apenas o TMPDIR_TESTE deste script, com validacao dupla.
limpar_home() {
  [ -n "${TMPDIR_TESTE:-}" ] && [ "$TMPDIR_TESTE" != "/" ] || return 0
  rm -rf "$TMPDIR_TESTE"
  unset TMPDIR_TESTE
}

# Roda um comando do repo com HOME apontando para o fake (so no filho).
# Uso: run_plexo <arg...>   ->  stdout/stderr em $RUN_OUT, rc em $RUN_RC
run_plexo() {
  RUN_OUT="$(cd "$REPO" && HOME="$TMPDIR_TESTE" "$@")" 2>&1
  RUN_RC=$?
}

echo "launcher: validacao de id (bug 1 e 2)"
# Bug 1: $id interpolado em python3 -c permitia injecao de codigo.
for evil in "a' or '1'=='1" "x'; import os; os.system('true'); print('" "';print(1)//"; do
  fake_home
  run_plexo ./plexo context init "$evil"
  rc=$RUN_RC; out="$RUN_OUT"
  if [ $rc -ne 0 ] && printf '%s' "$out" | grep -q "id inválido"; then
    ok "id malicioso rejeitado: ${evil:0:22}"
  else
    bad "id malicioso ACEITO: ${evil:0:22} (rc=$rc)"
  fi
  limpar_home
done

# Bug 2: $id ia cru para CONTEXTS_DIR/$id.md e escapava do diretorio.
fake_home
mkdir -p "$TMPDIR_TESTE/.plexo/alvo"
run_plexo ./plexo context init "../alvo/ESCAPOU"
rc=$RUN_RC; out="$RUN_OUT"
if [ $rc -ne 0 ] && [ ! -f "$TMPDIR_TESTE/.plexo/alvo/ESCAPOU.md" ]; then
  ok "path traversal barrado"
else
  bad "path traversal NAO barrado (rc=$rc)"
fi
limpar_home

echo "launcher: init exige task existente (bug 4)"
fake_home
run_plexo ./plexo context init TASK_QUE_NAO_EXISTE
rc=$RUN_RC; out="$RUN_OUT"
if [ $rc -ne 0 ] && [ ! -f "$TMPDIR_TESTE/.plexo/contexts/TASK_QUE_NAO_EXISTE.md" ]; then
  ok "init de task inexistente recusado"
else
  bad "init criou contexto orfao (rc=$rc)"
fi
limpar_home

echo "launcher: exit codes e uso"
fake_home
( cd "$REPO" && HOME="$TMPDIR_TESTE" ./plexo context show ) >/dev/null 2>&1
[ $? -ne 0 ] && ok "show sem id -> nao-zero" || bad "show sem id devia falhar"
( cd "$REPO" && HOME="$TMPDIR_TESTE" ./plexo context ) >/dev/null 2>&1
[ $? -eq 0 ] && ok "context sem subcmd imprime uso -> 0" || bad "context sem subcmd devia sair 0"
( cd "$REPO" && HOME="$TMPDIR_TESTE" ./plexo help ) >/dev/null 2>&1
[ $? -eq 0 ] && ok "help -> 0" || bad "help devia sair 0"
limpar_home

echo "launcher: sintaxe"
if bash -n "$LAUNCHER" 2>/dev/null; then ok "bash -n"; else bad "bash -n"; fi

echo
printf 'plexo launcher: %d passaram, %d falharam\n' "$PASS" "$FAIL"
[ "$FAIL" -eq 0 ] || exit 1