# RGRTU Source Discovery

Checked on 2026-06-29.

## Public access

- `https://postupai.rsreu.ru/robots.txt` returns `User-agent: *` and empty `Disallow`.
- `https://postupai.rsreu.ru/guest/competition-lists/20` returns HTTP 200 without auth.
- The page is a Laravel Livewire interface. The static HTML contains the component
  `competition-lists-common` and the subject dictionary.

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

Primary adapter for the first implementation is Livewire discovery plus a swappable competition
fetcher. The initial HTML reliably exposes subject ids, but exact list-card and row requests still
need a browser Network capture after selecting:

1. subject id;
2. `eduProgramForms` = очная;
3. `competitionTypes` = общий конкурс or по договору.

The code therefore keeps RGRTU fetching isolated in `app/rgrtu/` and starts with fixture-backed
parser tests. Browser fallback is intentionally blocked until a concrete Network request is
documented.

## Load limits

- Sequential requests only.
- User-Agent identifies the monitor.
- Scheduler interval: 120 minutes.
- No CAPTCHA bypass, no authenticated session reuse, no personal data storage.

