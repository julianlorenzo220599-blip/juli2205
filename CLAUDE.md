<!-- Snapshot sincronizado desde Google Drive: .claude/CLAUDE.md (fileId 1cgjd09gXI0-8rvO9fXw11-48opprr6nQ). Para re-sincronizar ver .claude/sync-drive-memory.md -->

# Claude Code — Reglas globales (Julian)

<!-- Aplica a TODOS los proyectos -->

## Comportamiento de respuesta
- Directo al resultado. Sin intro, sin cierre, sin frases de cortesía.
- No repetir información ya mencionada en el contexto.
- Código primero. Explicación solo si se pide explícitamente.
- Máximo conciso. Si se puede decir en 1 línea, no usar 3.
- Español rioplatense.

## Selección de modelo
| Tarea | Modelo |
|---|---|
| Arquitectura, planificación, diseño de sistemas, decisiones técnicas complejas | `claude-opus-4-5` |
| Generación de código, refactoring, debugging, tareas rutinarias | `claude-sonnet-4-5` |
| Respuestas rápidas, completions simples, ediciones menores | `claude-haiku-4-5` |

## Contexto del proyecto principal — FUDEX
- Plataforma de tecnología gastronómica para el mercado argentino
- Co-fundador: Julian (PM + diseño + decisiones técnicas). CTO: Mateo (backend)
- Monorepo: Turborepo + pnpm
- Stack: Next.js 14 (frontends), Express + Socket.io (API), PostgreSQL + Drizzle ORM
- Infra: Railway (API), Vercel (frontends)
- Agentes activos: Admin (admin.fudex.com.ar), Cocina (cocina.fudex.com.ar), Menú (QR)
- En desarrollo: agente Recepción (reservas + front-of-house)
- WhatsApp bot: Meta Cloud API + Claude Haiku como clasificador de intenciones
- UI: dark theme en todo el ecosistema admin

## Reglas de código
- Sin comentarios obvios en el código.
- Componentes funcionales React, hooks estándar.
- Tailwind utility-first, sin CSS externo salvo necesidad.
- SVG o URL directa para logos, nunca texto fallback.

## Memoria acumulada
@.claude/memory/MEMORY.md
