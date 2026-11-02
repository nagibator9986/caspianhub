#!/bin/sh
# Скачивает базу SQLite и загруженные файлы из работающего контейнера Railway.
# На сайте ничего не меняет. Запускать из каталога, привязанного к проекту (railway link).
set -e
OUT="${1:-caspianhub-backup-$(date +%Y%m%d-%H%M).tar.gz}"
railway ssh -- "cd /app && tar czf - instance app/static/uploads | base64" \
  | python3 -c "import base64,sys; sys.stdout.buffer.write(base64.b64decode(sys.stdin.read()))" > "$OUT"
tar tzf "$OUT" > /dev/null
echo "Копия сохранена: $OUT"
tar tzvf "$OUT" | grep -E "\.db$" || echo "ВНИМАНИЕ: файла базы в копии нет"
echo "Загруженных файлов: $(tar tzf "$OUT" | grep -c 'uploads/.*/[^.][^/]*$' || true)"
