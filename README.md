# Dash-BMW-e90

Проекты вокруг приборной панели BMW E90 и вывода на неё произвольных
параметров.

Щиток: семейство **KMBI_PL2** (`HKOML2`, `BKOML2`, `DKOML2`, `KOMBL2`),
микроконтроллер **Fujitsu/Spansion MB90F395HA** (F2MC-16LX, 512 КБ флеша
по адресам `0xF80000–0xFFFFFF`), диагностический SGBD **`KOMB87.prg`**.

---

## Цель

Программное обеспечение, позволяющее **заливать кастомную прошивку в приборку
по проводу, без программатора** — тот же класс продукта, что `xHP Flashtool`
(кастомные прошивки в АКПП ZF через D-CAN) и `MHD Flasher` (моторы N54/N55
через OBD).

Что должна уметь кастомная прошивка:

1. выводить **все доступные показатели** и в верхнюю, и в нижнюю часть дисплея;
2. менять отображение передачи: не просто `D`/`S`, а `D1…D6`, `S1…S6`;
3. выводить **8 передач** — требование свапа АКПП на ZF 8HP;
4. в перспективе — **генератор прошивки**: пользователь выбирает свою приборку
   (программа сама читает её версию), отмечает нужные параметры и получает
   готовый образ.

**Чего проект не делает:** не подбирает и не ломает RSA-ключи подписи BMW.
Задача — в другом классе: найти то, **что подпись не покрывает** (непокрытый
диапазон памяти либо непокрытую таблицу диапазонов). Именно так работают
коммерческие флешеры для BMW.

---

## Состояние

Проект в стадии **реверс-инжиниринга**. Читать и понимать — можно, писать
в приборку — пока нет.

Что уже установлено:

* защищённая область `0xFFC000–0xFFFFFF` (загрузчик и векторы CPU) **не
  пишется ни одним** штатным файлом обновления `.0pa`/`.0ba` — значит,
  её надо снять дампом;
* протокол прошивки разобран по SGBD: сервисы `$23`/`$34`/`$36`/`$3D`,
  рутины `$31` → `$02` ClearMemory, `$07` RequestForAuthentication,
  `$08` ReleaseAuthentication, `$09` CheckSignature, `$0A` статус;
* подписей **две и они раздельные** — `PAF` (Programm) и `DAF` (Daten);
* транспорт D-CAN делает сам кабель `K+DCAN`, от хоста нужен только BMW-FAST
  на 115200 8N1.

Ближайшая задача — снять дамп `0xFFC000–0xFFFFFF`:
[`docs/research/INSTRUCTION_READ_FLASH.md`](docs/research/INSTRUCTION_READ_FLASH.md).

---

## Структура

```
docs/                       Результаты реверса — смысловое ядро проекта
  BMW_KOMBI_PL2_RESEARCH.md          сводный справочник по платформе PL2
  BMW_KOMBI_FLASHER_PLAN.md          анализ, поверхность атаки, дорожная карта
  D-CAN_TRANSPORT_RESEARCH.md        протокол кабеля K+DCAN, BMW-FAST
  BMW_KOMBI_PL2_BOOTLOADER_SIGNATURE_RU.md   схемы подписи BMW, публичные эксплойты
  article/
    drive2_gear_box_article.html     готовая статья для Drive2 со всеми апдейтами
  research/
    ANALYSIS_NOTES.md                подробный журнал реверса (читать первым)
    HANDOFF.md                       конспект журнала
    KOMB87_JOBS.md                   список 140 джобов SGBD
    KOMB87_SGBD_FINDINGS.md          разбор SGBD: сегменты, рутины, телетраммы
    INSTRUCTION_READ_FLASH.md        пошаговая инструкция для Windows
    disasm/                          листинги ключевых джобов

can-display/                Модуль вывода параметров на физический экран (Arduino / PlatformIO)
  src/, lib/, include/               прошивка МК, обработчики K-CAN и PT-CAN
  cad/, docs/enclosure/              3D-модели и чертежи корпусов (SCAD, STL, SVG)
  docs/                              документация CAN-сигналов, распиновка

tools/                       Все вспомогательные программы, по одному подкаталогу на инструмент
  flasher/                          Приложение: чтение и (в перспективе) запись
    check_bmw_env.py                   проверка окружения: Python, api32.dll, EDIABAS,
                                       OBD.INI, COM-порт, кабель, SGBD приборки
    kombi_read_flash.py                чтение памяти через EDIABAS api32.dll
  re/                                Декодеры прошивок и SGBD
    parse_ihex.py                      .0pa/.0ba → карта памяти
    dump_flat.py, diff_hex.py          утилиты работы с образами
    f2mc_disasm.py                     декодер инструкций F2MC-16LX
    f2mc_cfg.py                        рекурсивный дизассемблер / поиск функций
    f2mc_batch.py, f2mc_family.py      пакетный анализ и сравнение семейств
    f2mc_compare.py, f2mc_pairdiff.py  структурное сравнение билдов
    f2mc_icalls.py                     анализ косвенных вызовов
    sgbd_disasm.py                     дизассемблер джобов SGBD (.prg)
  check_firmware/
    check_firmware.py                  сверка локальных образов по манифесту
  patcher/, fujitsu_uart_flasher/,
  bitmap_tool/, bench_cluster_emulator/,
  ui_simulator/                      остальные утилиты (см. их README)
  site/                              генераторы данных для сайта (см. ниже)

site/                        Статический сайт (GitHub Pages) — справочник,
                             эмулятор экрана, схема UART. index.html, reference/,
                             emulator/, uart/. Часть страниц генерируется
                             (см. «Сайт» ниже) — не редактируются руками.

tests/                       Юнит-тесты для tools/ (pytest)

firmware-manifest.json      SHA-256 образов, которые НЕ хранятся в репозитории
```

---

## Чего в репозитории нет

**Образов прошивок и файлов SP-Daten здесь нет и не будет.** `.0pa`, `.0ba`,
`KOMB87.prg`, `*.DAT`, `*.HIS`, `*.HWH` — собственность BMW, и публиковать их
нельзя. По той же причине не публикуются руководства производителей.

Вместо файлов лежит [`firmware-manifest.json`](firmware-manifest.json) с их
контрольными суммами SHA-256 — так результаты остаются воспроизводимыми.

Свои копии (из вашей установки BMW Standard Tools или пакета SP-Daten) положите
в `local-firmware/` и проверьте:

```bash
python tools/check_firmware/check_firmware.py --list     # что ожидается
python tools/check_firmware/check_firmware.py            # сверить local-firmware/
```

---

## Быстрый старт

### Инструменты разбора

Чистый Python, внешних зависимостей нет. `sgbd_disasm.py` дополнительно
использует парсер контейнера SGBD из проекта
[BimmerDaten](https://github.com/zer02dev/BimmerDaten):

```bash
git clone https://github.com/zer02dev/BimmerDaten
cd tools/re
python3 sgbd_disasm.py <путь>/KOMB87.prg --list
python3 sgbd_disasm.py <путь>/KOMB87.prg --job SPEICHER_LESEN
python3 f2mc_cfg.py <путь>/9316169A.0pa --range 0xF9C000,0xFF0000 --json out.json
```

### Чтение памяти приборки

Требуется **Windows**, установленные BMW Standard Tools и **32-битный Python**
(`pydiabas` загружает 32-битную `api32.dll`):

```bash
py -3-32 -m pip install -r tools/flasher/requirements.txt

# окружение целиком: Python, pydiabas, api32.dll, EDIABAS.INI, OBD.INI,
# COM-порт, драйвер кабеля, SGBD приборки в EcuPath
py -3-32 tools/flasher/check_bmw_env.py

# сверка проприетарных файлов с манифестом (по SHA-256: имена в установке
# SP-Daten отличаются от наших, поэтому поиск идёт по содержимому)
py -3-32 tools/flasher/check_bmw_env.py --firmware-scan "G:\SP-DATEN 67.1"

py -3-32 tools/flasher/kombi_read_flash.py --check
py -3-32 tools/flasher/kombi_read_flash.py --ident
py -3-32 tools/flasher/kombi_read_flash.py --segment LAR \
    --start 0xFFC000 --end 0x1000000 --out boot.bin
```

`check_bmw_env.py` проверяет установку BMW Standard Tools, `--check` у
`kombi_read_flash.py` — только Python и `pydiabas`. Код возврата:
0 — всё на месте, 1 — предупреждения (чаще всего не подключён кабель),
2 — критично, работать не получится. Приборку скрипт не опрашивает.

Подробная пошаговая инструкция, включая стенд на K-CAN:
[`docs/research/INSTRUCTION_READ_FLASH.md`](docs/research/INSTRUCTION_READ_FLASH.md).

### Разработка: lint и тесты

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt

ruff check tools tests   # статический анализ
pytest -q                # юнит-тесты (tests/)
```

CI (GitHub Actions, `.github/workflows/ci.yml`) гоняет оба шага на каждый push
и pull request на Python 3.10 и 3.12. Тесты покрывают чистую логику
(`tools/re/parse_ihex.py`, `dump_flat.py`, `diff_hex.py`, `f2mc_disasm.py`,
`tools/check_firmware/check_firmware.py`) — всё, что не требует Windows,
EDIABAS или подключённого кабеля.

---

## Сайт

Статический сайт в [`site/`](site/) — публичный справочный слой поверх
`docs/`: таблица джобов SGBD с поиском, карта служб KWP2000, известные
адреса патчей, эмулятор экрана щитка и схема UART-подключения. Публикуется
на GitHub Pages Actions-воркфлоу [`pages.yml`](.github/workflows/pages.yml)
при пуше в `main`
(после **однократной ручной настройки**: Settings → Pages → Build and
deployment → Source → **GitHub Actions** — сам воркфлоу включить Pages
из CLI не может).

Часть страниц **генерируется** из источников, которые и остаются истиной
(markdown-журнал реверса, `tools/ui_simulator/`) — после правок там нужно
пересобрать сайт:

```bash
python3 tools/site/build_jobs_data.py   # docs/research/KOMB87_JOBS.md -> site/reference/jobs-data.js
python3 tools/site/sync_emulator.py     # tools/ui_simulator/index.html -> site/emulator/simulator.html
```

CI проверяет синхронность обоих файлов (`--check`) на каждый push/PR — если
кто-то поправил источник и забыл пересобрать сайт, сборка покраснеет.

Локальный просмотр без сервера — просто откройте `site/index.html` в
браузере (сайт полностью статический, без зависимостей и build-шага).

---

## Смежные проекты

* [**bmw-e90-can-display**](https://github.com/RzhavoeZubilo/bmw-e90-can-display) —
  отдельный проект: дополнительный дисплей на Arduino Nano, слушает PT-CAN/K-CAN
  и показывает температуры и напряжение. Отдельный репозиторий, потому что это
  самостоятельная прошивка со своим жизненным циклом.
* [DBC-mega-merge](https://github.com/Maseg535/E90-and-e8x-DBC-mega-merge-project) —
  база описаний CAN-сигналов E9x.
* [BimmerDaten](https://github.com/zer02dev/BimmerDaten) — парсер EDIABAS `.prg`.
* [EdiabasLib](https://github.com/uholeschak/ediabaslib),
  [ediabasx](https://github.com/emdzej/ediabasx) — реализации транспорта и VM.

Все они подключены как внешние зависимости, а не вендорены в этот репозиторий.

---

## Лицензия

**GNU GPL-3.0** (см. [LICENSE](LICENSE)).

Это не формальность: `tools/re/sgbd_disasm.py` использует парсер контейнера SGBD
из BimmerDaten, который является портом BimmerDis, основанного на ediabaslib, —
оба под GPL-3.0. Использование такого модуля делает производной всю работу,
поэтому лицензия выбрана осознанно и совпадает с лицензиями соседних проектов.

---

## Предупреждение о рисках

* **`SPEICHER_SCHREIBEN`, `FLASH_LOESCHEN`, `FLASH_SCHREIBEN*` не запускать**
  до полного понимания модели восстановления: неудачная запись может оставить
  щиток неработоспособным, а программатора для восстановления нет.
* Все эксперименты с записью — **только на донорском щитке**.
* Загрузочная область `0xFFC000–0xFFFFFF` не должна перезаписываться ни при
  каких обстоятельствах, пока она не разобрана.
