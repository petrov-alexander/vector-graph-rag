# Vector and Graph Rag MCPs

## Index & Run MCPs
Change `.env` file, run `docker-compose` to start the MCPs.

```bash
docker compose --env-file .env up -d
```
Wait for `indexer` service to finish and `mcp-runtime` service to start.

## Register MCPs
### Claude
```bash
claude mcp add qdrant-semantic -- docker exec -i mcp-servers-runtime uvx mcp-server-qdrant
claude mcp add neo4j-architect -- docker exec -i mcp-servers-runtime uvx mcp-neo4j-cypher
```
### OpenCode
```bash
opencode mcp add qdrant-semantic -- docker exec -i mcp-servers-runtime uvx mcp-server-qdrant
opencode mcp add neo4j-architect -- docker exec -i mcp-servers-runtime uvx mcp-neo4j-cypher

```
## Master Prompt
```text
ALWAYS USE `qdrant-semantic` and `neo4j-architect` MCPs when working with code on the project.
```