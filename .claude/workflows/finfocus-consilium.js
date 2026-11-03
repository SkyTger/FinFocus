export const meta = {
  name: 'finfocus-consilium',
  description: 'Консилиум экспертов на разных моделях + 2 раунда критика по доработке FinFocus под реальные потребности владельца',
  whenToUse: 'Продуктовое решение FinFocus, где нужен взгляд нескольких профилей и критика',
  phases: [
    { title: 'Эксперты', detail: '4 профиля на разных моделях, независимо' },
    { title: 'Синтез', detail: 'модератор сводит позиции в проект решения' },
    { title: 'Критик', detail: '2 раунда критика ↔ модератор с ответами экспертов' },
  ],
}

const BRIEF = args.brief
const QUESTION = args.question
const COMMON = `Ты участник консилиума по проекту FinFocus (рабочая папка /home/skytiger/Projects/FinFocus). Только чтение: никаких правок файлов, коммитов, запусков приложения и обращений к боевой базе data/finfocus.db на запись. Личные финансовые данные владельца в веб-запросы не передавать. Отвечай по-русски, по существу, с опорой на проверяемые факты (файл:строка, расчёт, источник с пометкой [verified — URL]/[unverified]).

=== БРИФ ===
${BRIEF}

=== ВОПРОС КОНСИЛИУМУ ===
${QUESTION}`

const EXPERTS = [
  { key: 'pm', model: 'fable', role: 'Продакт-менеджер приложений личных финансов (PFM). Знаешь YNAB, Simple Safe-to-Spend, Monarch, Copilot, PocketGuard, Дзен-мани, CoinKeeper. Твой угол: какую одну механику пользователь ждёт, какие аналоги решают его вопрос и где они проваливаются, что из списка находок — ядро, а что шум. Можно сверить аналоги веб-поиском.' },
  { key: 'planner', model: 'opus', role: 'Семейный финансовый консультант-практик. Твой угол: методика — бюджет по циклам получки (5-е/20-е), конверты, дневной лимит, кредитки и заначка, нестабильный доход (больничный вместо зарплаты), разовые крупные траты. Проверь расчёты из брифа и журнала бюджета на корректность и скажи, какую методику приложение должно воплотить, чтобы владелец перестал уходить в минус.' },
  { key: 'arch', model: 'sonnet', role: 'Архитектор кода FinFocus (Python/Dash/SQLAlchemy). Прочитай app/services/money_layers_service.py, app/services/calendar_service.py, app/services/purchase_recommendation_service.py, app/models/database.py и knowledge-bank (.obsidian-docs/knowledge-bank/). Твой угол: что из предложенного ложится на существующую модель дёшево, что требует новой сущности/миграции, где риск регрессий (928 тестов), какой минимальный первый шаг технически честен. Оценки объёма — в файлах и днях.' },
  { key: 'ux', model: 'haiku', role: 'UX-дизайнер финансовых интерфейсов. Прочитай app/components/dashboard.py, app/assets/panel.css и design.md щитка (.obsidian-docs/discussions/_archive/dashboard-as-menu-2026-08-23/design.md). Твой угол: как показать «можно тратить сегодня» и «до какого дня тянуть», чтобы не было ложного «свободно 0»; где продукт не объясняет себя; как не наплодить «крутилок и вертелок», которых владелец не хочет.' },
]

const POSITION = {
  type: 'object',
  properties: {
    core_problem: { type: 'string', description: 'Главная проблема своими словами, 2-4 предложения' },
    proposals: { type: 'array', items: { type: 'object', properties: {
      title: { type: 'string' }, what: { type: 'string' }, why: { type: 'string' },
      cost: { type: 'string', description: 'малый/средний/большой + пояснение' },
      priority: { type: 'integer', description: '1 = первым' },
    }, required: ['title', 'what', 'why', 'cost', 'priority'] } },
    first_step_mvp: { type: 'string', description: 'Что сделать первым шагом и чётко что НЕ входит' },
    disagreements: { type: 'string', description: 'С чем в брифе/аудите не согласен и почему' },
    risks: { type: 'string' },
  },
  required: ['core_problem', 'proposals', 'first_step_mvp', 'disagreements', 'risks'],
}

phase('Эксперты')
const positions = await parallel(EXPERTS.map(e => () =>
  agent(`${COMMON}\n\n=== ТВОЯ РОЛЬ ===\n${e.role}\n\nСформулируй независимую позицию. Не подстраивайся под аудит ассистента — если он ошибается или упускает главное, скажи.`,
    { label: `эксперт:${e.key} (${e.model})`, phase: 'Эксперты', model: e.model, schema: POSITION })
    .then(p => p && ({ expert: e.key, model: e.model, ...p }))
))
const got = positions.filter(Boolean)
log(`Позиций получено: ${got.length}/${EXPERTS.length}`)

const MOD_INSTR = `Ты модератор консилиума (продуктовый лид FinFocus). Итог читает владелец — PM, сам код не пишет: язык человеческий, без имён функций, кроме ссылок файл:строка. Формат решения (markdown):
## Решение консилиума
1) Диагноз (3-5 предложений)
2) Что делаем первым — MVP: что входит / что НЕ входит / критерий «готово» глазами владельца (на его ноябрьских цифрах)
3) Порядок дальнейших шагов (таблица: шаг · зачем · объём · зависимости)
4) Что отвергли и почему
5) Разногласия, оставшиеся открытыми (кто за что), и вопросы владельцу (не больше 3)
6) Риски и как их проверим`

phase('Синтез')
let draft = await agent(`${COMMON}\n\n${MOD_INSTR}\n\nПозиции экспертов (JSON):\n${JSON.stringify(got, null, 1)}\n\nСведи в одно решение. Где эксперты расходятся — выбери с обоснованием или вынеси в п.5. Проверь ключевые утверждения экспертов о коде сам (чтение файлов), не принимай на веру.`,
  { label: 'модератор: синтез', phase: 'Синтез', model: 'opus' })

const CRIT = {
  type: 'object',
  properties: {
    verdict: { type: 'string', enum: ['READY', 'NEEDS_WORK'] },
    issues: { type: 'array', items: { type: 'object', properties: {
      severity: { type: 'string', enum: ['critical', 'major', 'minor'] },
      issue: { type: 'string' }, evidence: { type: 'string' }, suggestion: { type: 'string' },
    }, required: ['severity', 'issue', 'evidence', 'suggestion'] } },
    summary: { type: 'string' },
  },
  required: ['verdict', 'issues', 'summary'],
}

phase('Критик')
const rounds = []
for (let r = 1; r <= 2; r++) {
  const crit = await agent(`${COMMON}\n\nТы — критик (adversarial review). Файлы НЕ пиши. Раунд ${r} из 2. Разбери проект решения консилиума: противоречит ли он решениям владельца (быт не вносится операцией никогда; без лишних настроек-«крутилок»; находки не чинить заплатками), верны ли расчёты на ноябрьских цифрах, честен ли MVP по объёму и рискам для 928 тестов, не упущена ли более простая альтернатива, не раздут ли scope. Утверждения о коде проверяй чтением файлов. READY — только если критичных и major проблем нет.\n\n=== ПРОЕКТ РЕШЕНИЯ ===\n${draft}`,
    { label: `критик: раунд ${r}`, phase: 'Критик', agentType: 'critic', schema: CRIT })
  rounds.push(crit)
  if (!crit) break
  log(`Критик раунд ${r}: ${crit.verdict}, замечаний ${crit.issues.length}`)
  if (crit.verdict === 'READY' && r > 1) break
  draft = await agent(`${COMMON}\n\n${MOD_INSTR}\n\nТы модератор. Критик (раунд ${r}) вернул замечания. По каждому: прими и исправь решение, либо отклони с проверяемым обоснованием. Позиции экспертов для сверки:\n${JSON.stringify(got, null, 1)}\n\n=== ТЕКУЩЕЕ РЕШЕНИЕ ===\n${draft}\n\n=== КРИТИКА ===\n${JSON.stringify(crit, null, 1)}\n\nВерни полный обновлённый текст решения и в конце раздел «## Ответ критику (раунд ${r})» — таблица замечание · принято/отклонено · почему.`,
    { label: `модератор: правка после раунда ${r}`, phase: 'Критик', model: 'opus' })
}

return { experts: got.map(p => ({ expert: p.expert, model: p.model, core_problem: p.core_problem, first_step_mvp: p.first_step_mvp, disagreements: p.disagreements })), rounds: rounds.map(c => c && ({ verdict: c.verdict, n: c.issues.length, summary: c.summary, issues: c.issues })), final: draft }
