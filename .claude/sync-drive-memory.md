# Resincronizar memoria desde Google Drive

Las reglas globales (`/CLAUDE.md`) y la memoria (`/.claude/memory/MEMORY.md`) son snapshots de Google Drive. La fuente de verdad vive en Drive:

| Archivo en repo | Origen en Drive | fileId |
|---|---|---|
| `CLAUDE.md` | `.claude/CLAUDE.md` | `1cgjd09gXI0-8rvO9fXw11-48opprr6nQ` |
| `.claude/memory/MEMORY.md` | `memory/MEMORY.md` | `1sACgYFByXBMl6gOM2VDuLsA_cGRHQcXj` |

## Cómo resincronizar

Pedile a Claude en chat: **"resincronizá memoria desde Drive"**.

Claude usa el MCP de Google Drive (`mcp__…__download_file_content`) para releer ambos fileIds, sobrescribe los archivos del repo conservando el encabezado de procedencia, y hace commit en la rama actual. No requiere instalar nada ni configurar credenciales — el MCP ya viene conectado en las sesiones de Claude Code.

## Por qué snapshot y no lectura en vivo

Tener una copia en el repo asegura que las reglas se carguen al abrir cualquier sesión sobre `juli2205`, incluso si el MCP de Drive está caído o desconectado. La re-sync se hace bajo demanda cuando se actualice Drive desde otra PC.
