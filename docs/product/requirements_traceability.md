AI Exam Checker — матрица трассировки требований
Версия: 0.1, 2026-10-26. Эта матрица связывает требования ТЗ с источником, задачей реализации и способом проверки. Идентификаторы тестов — из technical_specification.md; ID задач — из mvp_scope.md.
1. Каталог источников
ID	Источник	Что подтверждает	Ограничение
CTX	[`PROJECT_CONTEXT.md`](../../PROJECT_CONTEXT.md)	Цель прототипа, аудитория, демонстрационный путь, ограниченный предметный объём, запрет реальных персональных данных, предварительный стек	Номер задания до завершения исследования не утверждён; стек предварительный
AC	[`ACCEPTANCE_CRITERIA.md`](../../ACCEPTANCE_CRITERIA.md)	Изображение → OCR → исправление; подтверждённое задание/критерии; объяснение на каждый критерий; evidence и confidence; сквозная демо	Не содержит численных метрик качества и готового UX/архитектурного контракта
SEC-DOC	[`SECURITY.md`](../../SECURITY.md)	Синтетические данные, отсутствие регистрации/персональных данных, проверки зависимостей/образов/секретов перед деплоем	Не заменяет детальный security review
ARCH	[`ARCHITECTURE.md`](../../ARCHITECTURE.md)	Последовательность исследование → требования → архитектура → параллельные потоки → интеграция	Схема этапов предварительная и требует атомарной декомпозиции
BOARD	[`TASK_BOARD.md`](../../TASK_BOARD.md)	Существующие рабочие этапы T-001—T-014 и роли	Задачи крупные; декомпозируются в этом ТЗ, доска пока не обновлялась
R-SCOPE	[`docs/research/exam_scope.md`](../research/exam_scope.md)	Рекомендация по ограничению задания 19 ЕГЭ-2026 и причины выбора	Полное условие/номер необходимо сверить с комплектом КИМ
R-CRIT	[`docs/research/criteria_analysis.md`](../research/criteria_analysis.md)	Краткий пересказ критерия S4, шкала 0–2, определение + факт, частные случаи и набор тестовых категорий	Пересказ, не замена первоисточнику; не переносить на 2027 без сверки
R-SRC	[`docs/research/official_sources.md`](../research/official_sources.md)	Реестр первоисточников S1–S7, URL, год и статус документов	ZIP КИМ-2026/открытого варианта не прочитан целиком; статус КИМ-2027 нужно перепроверить
R-OPEN	[`docs/research/open_questions.md`](../research/open_questions.md)	Нерешённые вопросы, экспертные вопросы, права использования и условия допуска	Пока ответы на блокирующие вопросы не получены, живое предметное оценивание не считается валидированным


2. Сокращения задач реализации
- IMP-001 — сверка первоисточников, точного задания, экспертные решения и версия критерия.
- IMP-002 — ADR архитектуры, API/data contract и согласование границ модулей.
- IMP-003 — UI-flow, прототип интерфейса и accessibility checklist.
- IMP-004 — каркас репозитория, конфигурация и CI.
- IMP-005 — предметный профиль, модель версий критериев и схемы результата.
- IMP-006 — безопасная загрузка, валидация и временное хранение изображения.
- IMP-007 — OCR-адаптер, измерение OCR и критические ошибки распознавания.
- IMP-008 — ручной ввод, отображение и корректировка OCR-текста.
- IMP-009 — оркестрация оценивания по подтверждённому профилю.
- IMP-010 — evidence, объяснения, source links и confidence semantics.
- IMP-011 — needs_review и экспорт пакета эксперту.
- IMP-012 — история сессии, события аудита и редактирование логов.
- IMP-013 — интеграционная проверка безопасности и privacy review.
- IMP-014 — экспертный набор оценки качества и metric harness.
- IMP-015 — публичный синтетический demo-flow и резервное поведение.
- IMP-016 — API/UI интеграция и end-to-end проверки.
- IMP-017 — контейнеризация, hardening, конфигурация и деплой.
- IMP-018 — релизная документация, эксплуатационные инструкции и release gate.
- IMP-019 — performance baseline, калибровка и отчёт по качеству модели.
3. Трассировка функциональных требований
Требование	Источник/основание	Реализация	Проверка
FR-001 — один профиль задания	CTX; R-SCOPE	IMP-001, IMP-005, IMP-008	TEST-002, TEST-012
FR-002 — год, версия и источник видимы	AC; R-SRC	IMP-003, IMP-005, IMP-010	TEST-012, TEST-015
FR-003 — оценивать только подтверждённый критерий	R-OPEN; R-SCOPE	IMP-001, IMP-005, IMP-009	TEST-001, TEST-015
FR-004 — запуск хранит версию критерия	R-CRIT; R-OPEN	IMP-005, IMP-012	TEST-001, TEST-015
FR-005 — ручной ввод	CTX; AC	IMP-008	TEST-002, TEST-012
FR-006 — загрузка изображения	CTX; AC	IMP-006, IMP-008	TEST-002–TEST-003, TEST-012
FR-007 — проверка типа/размера/декодирования	SEC-DOC; проектная security-мера	IMP-006, IMP-013	TEST-003, TEST-011
FR-008 — безопасный отказ для невалидного файла	SEC-DOC; AC	IMP-006, IMP-008	TEST-003
FR-009 — временная обработка изображений	SEC-DOC; R-OPEN	IMP-006, IMP-012, IMP-013	TEST-011
FR-010 — оценка только после подтверждения текста	AC; R-CRIT; R-OPEN	IMP-008, IMP-009	TEST-002, TEST-012
FR-011 — OCR или контролируемая ошибка	AC	IMP-007, IMP-008	TEST-002, TEST-004
FR-012 — редактирование OCR	AC	IMP-008	TEST-002, TEST-012
FR-013 — различать распознанный и подтверждённый текст	R-OPEN; проектное UX-решение	IMP-003, IMP-008	TEST-012, TEST-013
FR-014 — не исправлять исторический смысл молча	R-OPEN; R-CRIT	IMP-007, IMP-008	TEST-004, TEST-005
FR-015 — тест критичных OCR-искажений	R-CRIT (категория 10)	IMP-007, IMP-014, IMP-019	TEST-004, TEST-005
FR-016 — запуск по подтверждённому профилю	R-SCOPE; R-OPEN	IMP-005, IMP-009	TEST-001, TEST-002
FR-017 — шкала 0–2 для версии 2026	R-CRIT (S4); R-SCOPE	IMP-001, IMP-005, IMP-009	TEST-006–TEST-008
FR-018 — два аналитических компонента без самодельных весов	R-CRIT	IMP-001, IMP-009, IMP-010	TEST-006–TEST-009
FR-019 — частные случаи критерия	R-CRIT	IMP-001, IMP-009, IMP-014	TEST-006–TEST-008
FR-020 — смысловые переформулировки разрешены	R-CRIT	IMP-009, IMP-014	TEST-006–TEST-008
FR-021 — не вводить отдельный штраф за грамотность	R-CRIT; R-OPEN Q4	IMP-001, IMP-009, IMP-014	TEST-006–TEST-008
FR-022 — явные статусы результата	AC; проектное решение	IMP-005, IMP-009, IMP-010	TEST-001, TEST-002, TEST-012
FR-023 — неоднозначные случаи уходят на пересмотр	R-CRIT; R-OPEN	IMP-009, IMP-010, IMP-011	TEST-006–TEST-009
FR-024 — воспроизводимость параметров запуска	R-OPEN; проектная техническая мера	IMP-005, IMP-009, IMP-012	TEST-010, TEST-015
FR-025 — предупреждение об экспериментальности	R-OPEN, раздел 3–4; AC	IMP-003, IMP-015	TEST-012
FR-026 — объяснение по каждому компоненту	AC; R-CRIT	IMP-010	TEST-008–TEST-009, TEST-012
FR-027 — evidence действительно в тексте	AC; термин Evidence в CTX	IMP-010	TEST-009
FR-028 — ссылка на точную версию источника	AC; R-SRC	IMP-005, IMP-010	TEST-012, TEST-015
FR-029 — разделять цитату и интерпретацию модели	AC; проектное решение объяснимости	IMP-003, IMP-010	TEST-009, TEST-012
FR-030 — корректная семантика confidence	AC; R-OPEN	IMP-010, IMP-014, IMP-019	TEST-008, TEST-010
FR-031 — пользователь помечает нужду в эксперте	R-OPEN, раздел 4	IMP-011	TEST-002, TEST-012
FR-032 — фиксируется причина пересмотра	R-OPEN, раздел 4–5	IMP-011	TEST-002, TEST-012
FR-033 — экспорт с раскрытием содержимого	SEC-DOC; R-OPEN	IMP-011, IMP-013	TEST-002, TEST-011
FR-034 — нельзя открыть незащищённую панель эксперта	SEC-DOC; R-OPEN	IMP-011, IMP-013	TEST-011
FR-035 — нет обещания realtime moderation	CTX, раздел «не входит»; R-OPEN	IMP-003, IMP-011, IMP-015	TEST-012
FR-036 — история текущей сессии и demo-данных	Цель аудита в задании; проектное решение приватности	IMP-012, IMP-015	TEST-002, TEST-012
FR-037 — история версий не перезаписывается	Проектная трассируемость; R-OPEN	IMP-005, IMP-012	TEST-015
FR-038 — аудит действий	SEC-DOC; требования пользователя	IMP-012, IMP-013	TEST-011, TEST-012
FR-039 — не включать содержимое в логи	SEC-DOC; R-OPEN	IMP-012, IMP-013	TEST-011
FR-040 — не хранить ответы постоянно по умолчанию	CTX; SEC-DOC; R-OPEN	IMP-006, IMP-012, IMP-013	TEST-011
FR-041 — только синтетические/разрешённые примеры	CTX; SEC-DOC; R-OPEN	IMP-001, IMP-014, IMP-015	TEST-006–TEST-008, TEST-012
FR-042 — сквозная демо без регистрации	CTX; AC; SEC-DOC	IMP-003, IMP-015, IMP-016	TEST-012
FR-043 — не публиковать реальные ученические данные/неразрешённые материалы	SEC-DOC; R-OPEN, раздел 3	IMP-001, IMP-013, IMP-015	TEST-011, TEST-012
FR-044 — ограничения видны в UI и README	AC; R-OPEN	IMP-003, IMP-015, IMP-018	TEST-012
FR-045 — поля профиля/источника/статуса версии	R-SCOPE; R-SRC	IMP-001, IMP-005	TEST-001, TEST-015
FR-046 — критерии неизменяемы, изменения версионируются	R-OPEN; проектное управление версий	IMP-005, IMP-018	TEST-001, TEST-015
FR-047 — блокировка непроверенного профиля	R-OPEN; R-SCOPE	IMP-001, IMP-005, IMP-009	TEST-001, TEST-015
FR-048 — запись версии критерия и движка	R-OPEN; проектная воспроизводимость	IMP-005, IMP-012	TEST-010, TEST-015
FR-049 — сценарий demo без реальных данных	CTX; AC; SEC-DOC	IMP-015	TEST-012
FR-050 — синтетические эталонные ответы утверждены экспертом	R-CRIT; R-OPEN	IMP-001, IMP-014, IMP-015	TEST-006–TEST-008
FR-051 — честная обработка недоступности провайдера	AC; проектное эксплуатационное требование	IMP-007, IMP-009, IMP-015, IMP-017	TEST-002, TEST-012
FR-052 — нормальный/частичный/спорный demo-сценарии	AC; R-OPEN, раздел 4	IMP-014, IMP-015	TEST-006–TEST-008, TEST-012


4. Трассировка нефункциональных требований
Требование	Источник/основание	Реализация	Проверка
NFR-001 — метрики производительности после baseline	Условие пользователя о необоснованных порогах; проектное решение	IMP-019, IMP-018	TEST-014
NFR-002 — конфигурируемые лимиты	SEC-DOC; проектное решение	IMP-002, IMP-006, IMP-007, IMP-017	TEST-003, TEST-014
NFR-003 — безопасная деградация при ошибке провайдера	AC; эксплуатационное ограничение	IMP-007, IMP-009, IMP-015	TEST-002, TEST-012
NFR-004 — модульность и согласованные контракты	CTX, предварительный стек; ARCH; BOARD	IMP-002, IMP-004, IMP-016	TEST-001, TEST-002
NFR-005 — логи без содержимого ответа	SEC-DOC	IMP-012, IMP-013	TEST-011
NFR-006 — русский UI	CTX и целевая аудитория	IMP-003, IMP-008, IMP-015	TEST-012, TEST-013
NFR-007 — версия модели/критерия и регрессии	R-OPEN; проектная мера	IMP-005, IMP-014, IMP-019	TEST-010, TEST-015
NFR-008 — доступность UI	Требование пользователя; проектный UX-стандарт	IMP-003, IMP-016	TEST-013
NFR-009 — не обещать официальный результат	CTX; R-OPEN, раздел 3–4	IMP-003, IMP-015, IMP-018	TEST-012
NFR-010 — не предназначен для массовой нагрузки	CTX, конкурсная цель; ограничение пользователя	IMP-017, IMP-018	TEST-014, release checklist


5. Трассировка безопасности
Требование	Источник/основание	Реализация	Проверка
SEC-001 — не собирать личные данные	CTX; SEC-DOC	IMP-003, IMP-013, IMP-015	TEST-011, TEST-012
SEC-002 — синтетические/обезличенные данные	CTX; SEC-DOC; R-OPEN	IMP-001, IMP-014, IMP-015	TEST-006, TEST-011
SEC-003 — серверная проверка файла	SEC-DOC; стандартная проектная мера	IMP-006, IMP-013	TEST-003, TEST-011
SEC-004 — безопасная обработка пути/контента	Проектная security-мера	IMP-006, IMP-013, IMP-017	TEST-003, TEST-011
SEC-005 — секреты только через окружение	SEC-DOC, требование про секреты	IMP-004, IMP-017, IMP-018	TEST-011
SEC-006 — прозрачность внешнего провайдера	R-OPEN; проектная privacy-мера	IMP-002, IMP-007, IMP-013	TEST-011, provider configuration review
SEC-007 — исключить текст и секреты из логов	SEC-DOC; проектная privacy-мера	IMP-012, IMP-013	TEST-011
SEC-008 — нет открытых привилегированных операций	SEC-DOC; CTX без регистрации	IMP-011, IMP-013	TEST-011
SEC-009 — HTTPS/CORS/лимиты/error hygiene	SEC-DOC; проектные деплой-меры	IMP-013, IMP-017	TEST-011, deployment checklist
SEC-010 — аудит зависимостей, контейнеров, секретов	SEC-DOC	IMP-013, IMP-017, IMP-018	TEST-011, release checklist
SEC-011 — срок жизни временных данных и очистка	R-OPEN; требования к приватности	IMP-006, IMP-012, IMP-013	TEST-011
SEC-012 — явное подтверждение экспорта	SEC-DOC; UX privacy design	IMP-003, IMP-011	TEST-002, TEST-011


6. Трассировка UX
Требование	Источник/основание	Реализация	Проверка
UX-001 — последовательный вводной поток	CTX; AC	IMP-003, IMP-008, IMP-016	TEST-012
UX-002 — различать OCR и подтверждённый текст	AC; R-OPEN	IMP-003, IMP-008	TEST-012, TEST-013
UX-003 — понятные безопасные ошибки	SEC-DOC; AC	IMP-003, IMP-006, IMP-007, IMP-008	TEST-002, TEST-003, TEST-013
UX-004 — предварительный статус и источник	AC; R-OPEN	IMP-003, IMP-010, IMP-015	TEST-012
UX-005 — отделить evidence от объяснения	AC	IMP-003, IMP-010	TEST-009, TEST-012
UX-006 — нейтральная обработка спорных случаев	R-CRIT; R-OPEN	IMP-003, IMP-010, IMP-011	TEST-006–TEST-009, TEST-012
UX-007 — основные операции доступны с клавиатуры	Требование пользователя; accessibility design	IMP-003, IMP-016	TEST-013
UX-008 — не кодировать статус только цветом	Accessibility design	IMP-003, IMP-016	TEST-013
UX-009 — адаптивное размещение	UX requirement	IMP-003, IMP-016	TEST-013
UX-010 — быстрый demo без персональных данных	CTX; SEC-DOC; AC	IMP-003, IMP-015	TEST-012


7. Трассировка требований к тестированию
Требование	Источник/основание	Реализация	Проверка/артефакт
TEST-001 — unit-тесты предметных и контрактных правил	FR/NFR из этого документа	IMP-005, IMP-009, IMP-016	CI unit report
TEST-002 — API сценарии успеха и отказа	AC; UC-01—UC-04	IMP-006–IMP-012, IMP-016	API integration report
TEST-003 — негативные file tests	SEC-003/004	IMP-006, IMP-013	Negative upload test report
TEST-004 — OCR challenge set	R-CRIT, категория 10; AC	IMP-007, IMP-014	Versioned OCR dataset manifest
TEST-005 — измерить OCR CER/WER и критичные искажения	Условие пользователя: измеримость без выдуманных порогов	IMP-007, IMP-014, IMP-019	OCR evaluation report; target pending baseline
TEST-006 — набор категорий оценки	R-CRIT, категории 1–10	IMP-001, IMP-014	Labelled case catalogue
TEST-007 — экспертный gold label	R-OPEN, expert questions	IMP-001, IMP-014	Expert-approved labels and adjudication log
TEST-008 — оценить совпадение и ошибочные классы	R-OPEN; требование пользователя об измерении качества	IMP-014, IMP-019	Evaluation metrics report; thresholds pending
TEST-009 — evidence принадлежит тексту	AC; Evidence definition in CTX	IMP-010, IMP-014	Unit/API assertions and reviewed examples
TEST-010 — регрессии при изменении модели/промпта	R-OPEN; NFR-007	IMP-014, IMP-019	Regression report attached to candidate release
TEST-011 — security/privacy tests	SEC-DOC	IMP-013, IMP-017	Security checklist/report
TEST-012 — full end-to-end demo	AC	IMP-015, IMP-016	Recorded/automated acceptance run
TEST-013 — usability/accessibility tests	UX requirements	IMP-003, IMP-016	Accessibility checklist and defects list
TEST-014 — performance measurements	User rule on justified thresholds; NFR-001/002	IMP-019	Reproducible benchmark report
TEST-015 — old criteria version stays pinned	FR-004, FR-037, FR-046–048	IMP-005, IMP-012	Version migration/regression tests
TEST-016 — release gate	SEC-DOC; OPS requirements	IMP-017, IMP-018	Release checklist with test status


8. Трассировка эксплуатационных требований
Требование	Источник/основание	Реализация	Проверка
OPS-001 — stack finalised in ADR	CTX; ARCH	IMP-002, IMP-004	ADR accepted before skeleton/API code
OPS-002 — env config and safe .env.example	SEC-DOC	IMP-004, IMP-017	Secret scan; startup config test
OPS-003 — local setup reproducible	BOARD; user request to deploy	IMP-004, IMP-018	Clean-environment smoke test
OPS-004 — minimal container privileges and storage policy	SEC-DOC; project security	IMP-017	Container review and file lifecycle tests
OPS-005 — health/readiness without secrets	Deployment design	IMP-017	Endpoint smoke test
OPS-006 — deploy, smoke test and rollback	BOARD T-014; user scope	IMP-017, IMP-018	Deployment rehearsal record
OPS-007 — documented demo-only limits	CTX; NFR-010	IMP-017, IMP-018	README/deploy checklist review
OPS-008 — retention and incident process	SEC-DOC; R-OPEN	IMP-013, IMP-017, IMP-018	Retention/secret-rotation checklist and test


9. Нерешённые вопросы как явные блокеры
Вопрос	Где зафиксирован	Владелец решения	Блокирует	Требуемое свидетельство закрытия
OPEN-001: точный номер/условие и соответствие КИМ с руководством	docs/research/open_questions.md, Q2	Research + предметный эксперт	Профиль критериев и живое оценивание	Записаны название, версия/дата документов, страница/раздел и экспертная подпись/аппрув
OPEN-002: статус окончательного ЕГЭ-2027	docs/research/open_questions.md, Q1/Q3	Research	Любое объявление поддержки ЕГЭ-2027	Повторная проверка официальной страницы и файлов, версия источника в реестре
OPEN-003: пограничные случаи и грамотность	docs/research/open_questions.md, Q4 и вопросы эксперту	Предметный эксперт	Утверждённый evaluation engine	Письменные правила/решения и примеры с эталонной оценкой
OPEN-004: права использования материалов	docs/research/open_questions.md, раздел 3	Product owner/legal reviewer	Публичный корпус и эталоны	Правовое основание или замена на синтетические материалы
OPEN-005: экспертная разметка и арбитраж	docs/research/open_questions.md, вопрос 7	Research + эксперты	Заявление метрик качества	Документированный протокол разметки и разрешения разногласий
OPEN-006: провайдеры и обработка данных	docs/research/open_questions.md + SECURITY.md	Architect + Security	Реальная загрузка/внешний API	ADR с потоками данных, настройками и privacy disclosure
OPEN-007: API, схема данных, историю и аудит	PROJECT_CONTEXT.md; ARCHITECTURE.md	Architect	Параллельная реализация frontend/backend	Принятый API contract и data model
OPEN-008: пороги качества/производительности	docs/research/open_questions.md; NFR-001	QA + product owner	Публичное заявление о качестве/производительности	Отчёт baseline, выбранные пороги с обоснованием и решение о допуске


10. Правила поддержания матрицы
1. Новое требование не принимается без источника/обоснования, задачи реализации и проверяемого теста или явно помеченного способа ручной проверки.
2. Изменение версии критерия должно обновлять FR-045–FR-048, тесты регрессии и профиль применимости. Прошлые результаты не переписываются.
3. После выполнения задачи интегратор отмечает её фактический commit/PR и CI run в рабочей доске; текущая матрица — план, а не подтверждение выполнения.
4. Если требование блокируется открытым вопросом, это остаётся видимым в задаче и release gate. Нельзя закрывать его только потому, что код компилируется.