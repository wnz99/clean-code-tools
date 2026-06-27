#!/usr/bin/env bash
set -euo pipefail

http_port="${WEAVIATE_HTTP_PORT:-8080}"
base_url="http://127.0.0.1:${http_port}"

ready_url="${base_url}/v1/.well-known/ready"
meta_url="${base_url}/v1/meta"
ready=false

for _attempt in $(seq 1 60); do
  if curl -fsS "${ready_url}" >/dev/null 2>&1; then
    ready=true
    break
  fi
  sleep 1
done

if [[ "${ready}" != "true" ]]; then
  echo "Weaviate did not become ready at ${base_url}" >&2
  curl -sS "${ready_url}" || true
  exit 1
fi

curl -fsS "${meta_url}" | python3 -m json.tool >/dev/null

echo "Weaviate ready at ${base_url}"

