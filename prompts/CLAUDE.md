# prompts — CLAUDE.md

Parent first: корневой [CLAUDE.md](../CLAUDE.md) (§ Bootstrap → Danger Zones → Critical Rules). Этот файл — локальные дополнения, не дублирует root.

## Назначение

`prompts/` хранит переиспользуемые промпты (input prompts), написанные оператором, для AI-агентов (Claude Code / Codex / Cursor). Это поверхность, редактируемая человеком: файлы создаёт и редактирует оператор.

AI трогает содержимое `prompts/` только по явному запросу оператора (создать новый prompt, отредактировать существующий).

## Что сюда кладётся

- Markdown-файлы с переиспользуемыми промптами: инструкции агенту, шаблоны задач, переиспользуемые фрагменты контекста.
- Примеры: «провести аудит модуля по чек-листу», «подготовить скелет нового фича-модуля».
- Имя — human-readable топик: `review_module.md`, `audit_realm.md`, `module_skeleton.md`.

## Что НЕ кладётся сюда

- Ephemeral AI output (аудиты / планы / completion reports / findings). Routing — `ai_reports/audits/` (аудиты), `ai_reports/tasks/` (планы); completion report по умолчанию в чат (canonical — root `CLAUDE.md § Output placement`).
- Permanent canonical docs (policy, runbooks, registries) — `docs/` (routing — `docs/ai/DOC_ROUTING.md`).
- Секреты / API keys / значения из plist-файлов — запрещено (`[CR-SECRETS]`).

## Naming

- Переиспользуемый prompt: осмысленное имя без даты, snake_case, расширение `.md` (промпт переиспользуется, не ephemeral).
- Дата в имени (`YYYY-MM-DD_…`) — только для `ai_reports/` (canonical правило — root `§ Output placement`).

## Границы файла

Не расширять до cross-cutting discipline / правил обновления документации / verification — это owner docs (`docs/ai/DOCS_MAINTENANCE.md`, `docs/VERIFICATION.md`, root `CLAUDE.md`).
