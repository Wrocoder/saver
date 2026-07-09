# Money Saver Development Tasks

Этот файл является рабочим чеклистом проекта. После завершения задачи меняй `[ ]` на `[x]` и добавляй краткую заметку, если решение важно для будущей разработки.

## Правила ведения

- `[x]` задача завершена и проверена.
- `[ ]` задача ещё не завершена.
- Новые задачи добавлять в ближайший релевантный раздел.
- Если задача меняет API, модель данных или пользовательский сценарий, обновлять `README.md` и тесты.
- Перед отметкой `[x]` запускать релевантные проверки: backend tests, frontend build, smoke-check сервера.

## Завершено

- [x] Базовый FastAPI backend.
- [x] React + TypeScript frontend на Vite.
- [x] Локальная SQLite-конфигурация с готовностью к PostgreSQL через SQLAlchemy.
- [x] Alembic migrations.
- [x] Пользователи, профиль и базовая валюта.
- [x] Регистрация, вход, refresh/logout.
- [x] JWT access tokens и hashed refresh tokens.
- [x] Создание финансовых целей.
- [x] Редактирование целей.
- [x] Архивирование целей без удаления истории операций.
- [x] Список целей и прогресс-бары.
- [x] Ручные пополнения целей.
- [x] Отмена ошибочной операции пополнения.
- [x] История операций по цели.
- [x] Приоритеты целей.
- [x] Строгая стратегия распределения денег.
- [x] Пропорциональная стратегия распределения денег.
- [x] Расчёт ожидаемой даты достижения цели.
- [x] Расчёт необходимого ежемесячного платежа.
- [x] Сценарий изменения доступной месячной суммы.
- [x] Профиль доходов, расходов, долгов и финансовой подушки.
- [x] Расчёт безопасной месячной суммы накоплений.
- [x] Валюты и ручные курсы обмена.
- [x] Мультивалютные операции с сохранением применённого курса.
- [x] JSON export пользовательских данных.
- [x] Product analytics events для ключевых действий.
- [x] In-app notifications на основе текущего плана.
- [x] Пользовательские настройки уведомлений.
- [x] Recurring savings rules.
- [x] Применение recurring rule как реального пополнения.
- [x] Месячные отчёты по прогрессу и операциям.
- [x] История изменения цены цели.
- [x] Автоматическая запись истории цены при изменении `target_amount`.
- [x] CSV export целей.
- [x] CSV export операций накопления.
- [x] CSV import целей с построчной валидацией.
- [x] Frontend Data panel для CSV export/import.
- [x] Backend test coverage для planning, auth, finance, currency, export, notifications, recurring rules, reports, price history и CSV.
- [x] Frontend production build проходит.
- [x] Локальные серверы запускаются на `8001` и `5173`.

## Ближайший MVP Backlog

- [x] Drag-and-drop изменение порядка целей во frontend.
- [x] Endpoint для пакетного сохранения порядка целей из drag-and-drop.
- [x] UI для выбора стратегии распределения: strict priority / proportional.
- [x] UI для настройки процентов proportional allocation.
- [x] Детальная страница цели или расширяемая карточка цели.
- [x] Экран месячного финансового плана с календарём пополнений.
- [x] Planned vs actual пополнения в UI.
- [x] Simple notification scheduler вместо ручной генерации уведомлений.
- [x] Хранение notification delivery preferences по каналам и частоте.
- [x] CSV import исторических операций накопления.
- [x] CSV шаблон для импорта целей.
- [x] CSV шаблон для импорта операций.
- [x] Улучшить ошибки импорта CSV: номер строки, поле, исходное значение.
- [x] Export выбранного периода операций.
- [x] Basic product analytics dashboard для MVP-метрик.
- [x] Audit log viewer для пользователя.
- [x] Account deletion endpoint.
- [x] User data export download из backend напрямую без повторной JSON-сборки во frontend.
- [x] PWA manifest и базовый service worker.
- [x] Responsive pass для мобильных экранов 360px и 768px.
- [x] Accessibility pass: labels, focus states, keyboard navigation.
- [x] Empty/loading/error states для всех панелей.
- [x] E2E smoke tests для auth, goal creation, contribution, CSV export/import.

## Расчётный Модуль

- [x] Покрыть тестами edge cases: нулевая доступная сумма, достигнутые цели, просроченные deadline.
- [x] Поддержать стратегию `nearest_deadline`.
- [x] Поддержать стратегию `smallest_goal_first`.
- [x] Поддержать custom fixed amount allocation.
- [x] Добавить моделирование разовых поступлений.
- [ ] Добавить моделирование пропущенных месяцев.
- [ ] Добавить cautious / realistic / optimistic scenario presets.
- [ ] Добавить вероятность достижения цели в срок на основе сценариев.
- [ ] Добавить explainability payload: какие входные данные повлияли на дату цели.
- [ ] Добавить предупреждения о конфликтующих целях.
- [ ] Добавить рекомендации при невозможности достичь цель в срок.

## Финансовая Безопасность

- [ ] Расширить financial emergency fund UX.
- [ ] Рекомендация создать финансовую подушку как отдельную цель.
- [ ] Мягкие предупреждения, если план использует весь свободный остаток.
- [ ] Правила минимального остатка, который нельзя распределять.
- [ ] Более строгая логика дорогого просроченного долга.
- [ ] Отдельные предупреждения по high-interest debt.

## Валюты и Цены

- [ ] Источник и дата курса в UI рядом с пересчётом.
- [ ] Предупреждение о сильном изменении курса.
- [ ] Неизменяемая история курса для операций.
- [ ] История цены цели в графике.
- [ ] Desired purchase price для цели.
- [ ] Price drop notification.
- [ ] Product URL tracking adapter interface.
- [ ] Первая реализация price tracking через ручное обновление или stub provider.

## Доходы, Расходы и Импорт

- [ ] CSV import расходов.
- [ ] CSV import доходов.
- [ ] CSV import долгов.
- [ ] Mapping UI для CSV колонок.
- [ ] Категории расходов.
- [ ] Обнаружение повторяющихся расходов.
- [ ] Обнаружение подписок.
- [ ] Рекомендации по расходам на основе последних 3 месяцев.
- [ ] Open Banking provider abstraction.
- [ ] Open Banking integration spike без хранения банковских логинов.

## AI Assistant

- [ ] Подготовить контракт AI context payload из расчётного модуля.
- [ ] AI endpoint для объяснения плана без изменения данных.
- [ ] Guardrails: AI не выполняет расчёты вместо engine.
- [ ] Guardrails: AI не меняет план без подтверждения пользователя.
- [ ] UI чата помощника.
- [ ] Prompt templates для объяснения просрочки, перераспределения бонуса и safe spend.
- [ ] Логи AI-рекомендаций без хранения лишних чувствительных данных.

## Совместные Цели

- [ ] Data model и миграции для shared goals.
- [ ] Роли участников: owner, editor, viewer.
- [ ] Invite flow.
- [ ] История вкладов по участникам.
- [ ] Audit trail изменений совместной цели.
- [ ] Разграничение доступа к shared goals.
- [ ] Уведомления участников.

## Подписка и Монетизация

- [ ] Free/paid feature flags.
- [ ] Subscription model в UI.
- [ ] Pricing page внутри приложения.
- [ ] Ограничение активных целей для free tier.
- [ ] Paid gates для advanced scenarios.
- [ ] Paid gates для multicurrency advanced features.
- [ ] Paid gates для AI assistant.
- [ ] Paid gates для price tracking.
- [ ] Billing provider selection.
- [ ] Subscription webhook handling.

## Безопасность и Privacy

- [ ] Enforce `DEV_AUTH_FALLBACK_ENABLED=false` outside local development.
- [ ] Strong `SECRET_KEY` validation на старте production.
- [ ] 2FA design и backend endpoints.
- [ ] Active sessions management.
- [ ] Rate limiting for auth endpoints.
- [ ] Password reset flow.
- [ ] Email verification.
- [ ] GDPR consent fields.
- [ ] Data retention policy.
- [ ] Backup and restore procedure.
- [ ] Field-level review чувствительных данных перед production.
- [ ] Security headers.
- [ ] Production CORS allowlist.

## Архитектура и Инфраструктура

- [ ] PostgreSQL docker-compose для локальной разработки.
- [ ] Redis docker-compose.
- [ ] Background worker setup.
- [ ] Scheduled jobs для уведомлений.
- [ ] Object storage abstraction для экспортов.
- [ ] Structured logging.
- [ ] Error monitoring.
- [ ] API pagination для длинных списков.
- [ ] API filtering/sorting для goals, contributions, notifications.
- [ ] OpenAPI review для мобильных клиентов.
- [ ] CI pipeline: backend tests.
- [ ] CI pipeline: frontend build.
- [ ] CI pipeline: lint/type checks.
- [ ] Deployment plan for staging.
- [ ] Deployment plan for production.

## UX/UI

- [ ] Быстрый расчёт без регистрации.
- [ ] Сохранение первого расчёта после регистрации.
- [ ] Короткий onboarding.
- [ ] Настройка основной валюты в onboarding.
- [ ] Создание первой цели в onboarding.
- [ ] Главная панель: next best action.
- [ ] Главная панель: safe-to-spend amount.
- [ ] Главная панель: цели, которые отстают.
- [ ] Финансовый календарь.
- [ ] Архив достигнутых целей.
- [ ] Улучшить визуальное завершение цели.
- [ ] Milestones 25/50/75/100%.
- [ ] Calendar streaks без манипулятивной геймификации.
- [ ] Copywriting pass: простой язык без финансового жаргона.
- [ ] Visual regression screenshots для desktop/mobile.

## Тестирование

- [ ] Unit tests для всех allocation strategies.
- [ ] Unit tests для scenarios.
- [ ] Unit tests для currency edge cases.
- [ ] Unit tests для CSV import validation edge cases.
- [ ] API tests для account deletion/export privacy.
- [ ] API tests для shared goals access control.
- [ ] API tests для notification settings.
- [ ] Frontend component tests для ключевых форм.
- [ ] E2E tests для onboarding.
- [ ] E2E tests для планирования нескольких целей.
- [ ] E2E tests для импорта/экспорта.

## Запуск MVP

- [ ] Определить MVP success metrics dashboard.
- [ ] Настроить события: first goal created.
- [ ] Настроить события: second goal created.
- [ ] Настроить события: contribution added.
- [ ] Настроить события: weekly/monthly return.
- [ ] Настроить события: scenario used.
- [x] Настроить события: priority changed.
- [ ] Настроить события: CSV/JSON export used.
- [ ] Alpha test на локальной/staging среде.
- [ ] Собрать feedback по созданию первой цели.
- [ ] Собрать feedback по пониманию плана.
- [ ] Исправить top onboarding blockers.
- [ ] Подготовить MVP release notes.
- [ ] Подготовить privacy policy draft.
- [ ] Подготовить terms draft.
