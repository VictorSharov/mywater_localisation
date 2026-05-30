<!--
doc-role: child
doc-owner: prompts/CLAUDE.md (mywater_localisation repo)
doc-scope: локальные правила директории prompts/ (переиспользуемые операторские промпты). Не дублирует root CLAUDE.md.
-->

# prompts — CLAUDE.md

Parent first: корневой [CLAUDE.md](../CLAUDE.md) (§ Bootstrap → § Task router → § Critical rules). Этот файл — локальные дополнения, не дублирует root.

## Назначение

`prompts/` хранит переиспользуемые промпты (input prompts), написанные оператором, для AI-агентов (Claude Code / Codex / Cursor). Это поверхность, редактируемая человеком: файлы создаёт и редактирует оператор.

AI трогает содержимое `prompts/` только по явному запросу оператора (создать новый prompt, отредактировать существующий).

## Что сюда кладётся

- Markdown-файлы с переиспользуемыми промптами: инструкции агенту, шаблоны задач, переиспользуемые фрагменты контекста.
- Примеры: [`localisation_verification.md`](localisation_verification.md) (проверка перевода); промпт на translation pass / audit pass.
- Имя — human-readable топик, snake_case, расширение `.md`.

## Что НЕ кладётся сюда

- Ephemeral AI output (черновики, дампы, one-off анализ, completion reports / findings) — в `/tmp`, не в дерево репозитория (root `CLAUDE.md`, правило «Scratch stays out of the working tree», в шапке); completion report по умолчанию в чат.
- Permanent canonical docs (контракт / механика корпуса / канон стиля / экспорт) — top-level `CLAUDE.md` / `PIPELINE.md` / `TRANSLATION_STYLE.md` / `EXPORT.md` / `README.md` (навигация — root `CLAUDE.md § Task router`).
- Секреты / API-токены / значения plist-файлов — запрещено (`[CR-SECRETS]`).

## Naming

- Переиспользуемый prompt: осмысленное имя без даты, snake_case, расширение `.md` (промпт переиспользуется, не ephemeral).

## Границы файла

Не расширять до cross-cutting discipline / правил пайплайна / verification — это owner docs (`CLAUDE.md`, `PIPELINE.md`, root `CLAUDE.md § Verification`).
