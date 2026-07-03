# RGRTU Source Discovery

Checked on 2026-07-03.

## Public access

- `https://postupai.rsreu.ru/robots.txt` returns `User-agent: *` and empty `Disallow`.
- `https://postupai.rsreu.ru/guest/competition-lists/20` returns HTTP 200 without auth.
- The page is a Laravel Livewire interface. The static HTML contains the component
  `competition-lists-common`, the subject dictionary, and the `competitions` payload.
- Concrete public lists are available as
  `https://postupai.rsreu.ru/guest/competition-lists/20/{competition_id}`.

## Campaign and subject ids observed

Current public campaign id observed from the page: `20`.

Tracked subjects:

| Code | Subject id | Title |
|---|---:|---|
| 01.03.02 | 1569730463748068670 | Прикладная математика и информатика |
| 02.03.02 | 1569730463774283070 | Фундаментальная информатика и информационные технологии |
| 09.03.01 | 1569730463884383550 | Информатика и вычислительная техника |
| 09.03.02 | 1569730463890675006 | Информационные системы и технологии |
| 09.03.03 | 1569730463895917886 | Прикладная информатика |

## Adapter decision

Primary adapter reads the initial `competition-lists-common` payload from
`/guest/competition-lists/20`. In the default `general` scope, for each tracked program it selects
the очная competition by:

1. direction code;
2. competition code `04` for общий конкурс;
3. configured number of places, which disambiguates profiles with the same direction code.

The `all` scope first finds the tracked full-time profile by the same general-competition anchor,
then includes every competition category with the same `eduPrograms[].id`: quotas, target admission,
general competition, and contract categories.

The selected payload contains official `submitted` and `taken` counters plus entrant rows. The bot
uses `submitted` for `Подано заявлений` so source failures are distinct from a real zero. Direct
competition URLs are kept as `source_url` values for diagnostics and manual checks.

## Load limits

- Sequential requests only.
- User-Agent identifies the monitor.
- Scheduler interval: 120 minutes.
- No CAPTCHA bypass, no authenticated session reuse, no personal data storage.
