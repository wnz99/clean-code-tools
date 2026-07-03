FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app/src/python
ENV WEAVIATE_URL=http://weaviate:8080
ENV CLEAN_CODE_MCP_HOST=0.0.0.0
ENV CLEAN_CODE_MCP_PORT=8765

WORKDIR /app

RUN python -m pip install --no-cache-dir \
    "fastembed>=0.8.0" \
    "fastmcp>=2.0.0" \
    "httpx>=0.27.0" \
    "pydantic>=2.12.0"

COPY runtime/ /app/

EXPOSE 8765

CMD ["python", "scripts/docker_mcp_server.py"]
