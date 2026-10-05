# `komb87.prg`: что удалось извлечь

Результат разбора SGBD приборки KOMBI (KOMB87) из присланных файлов.
Все данные — воспроизводимые: команды приведены в конце каждого раздела.

---

## 1. Какие файлы получены

| Путь | Дата | Размер | MD5 | Версия |
|---|---|---|---|---|
| `/Volumes/Новый том/BMW SP-Daten 69.0/E89/ecu/KOMB87.prg` | 13.10.2021 | 1 282 130 | `3356dc76…` | **основная** |
| `/Volumes/Новый том 1/BMW/Rheingold/Ecu/komb87.prg` | 12.05.2020 | 1 282 130 | `3356dc76…` | **идентична** |
| `/Volumes/Новый том/BMW Standard Tools/EDIABAS/ECU_20241128_215934/KOMB87.prg` | 13.11.2019 | 829 559 | `b4bdee82…` | отдельная |
| `/Volumes/Новый том/BimmerGeeks Standard Tools/EDIABAS/ECU/KOMB87.prg` | 07.09.2016 | 821 780 | `8011056f…` | отдельная |

Итого **три различные версии**. Копии заведены в
`прошивки приборок/SGBD/` с говорящими именами; дизассемблированные джобы —
в `прошивки приборок/SGBD/disasm/`.

Новый инструмент: `прошивки приборок/tools/sgbd_disasm.py` — дизассемблер
джобов BEST/1 с адресами и разрешёнными целями переходов, плюс дамп
расшифрованных байт по диапазону.

```bash
python3 tools/sgbd_disasm.py SGBD/KOMB87_spdaten69.prg --list
python3 tools/sgbd_disasm.py SGBD/KOMB87_spdaten69.prg --job SPEICHER_LESEN
python3 tools/sgbd_disasm.py SGBD/KOMB87_spdaten69.prg --raw 0x1B274,0x1B3FF
```

## 2. Метаданные основной версии

```
BIP:            07.01.00
Ревизия:        5.2
Автор:          Eurospace EI-42 Kugelmann, Eurospace EI-42 Kuppe, Bertrandt EI-…
Последнее изм.: Wed Nov 20 10:37:09 2013
Джобов:         140
Таблиц:         33
```

---

## 3. Карта служб и routine ID — главный результат

Джобы и их официальные комментарии (это документация BMW, а не наш вывод):

| Джоб | Служба KWP2000 | ID / routine | Фрагмент телетраммы |
|---|---|---|---|
| `SPEICHER_LESEN` | **`$23` ReadMemoryByAddress** | — | `86 FF F1 23 …` |
| `SPEICHER_SCHREIBEN` | **`$3D` WriteMemoryByAddress** | — | `80 FF F1 …` (длина переменная) |
| `AUTHENTISIERUNG_ZUFALLSZAHL_LESEN` | `$31` StartRoutineByLocalIdentifier | **`$07` RequestForAuthentication** | `83 FF F1 31 07 00` |
| `AUTHENTISIERUNG_START` | `$31` | **`$08` ReleaseAuthentication** | ключ передаётся в `BINAER_BUFFER` |
| `FLASH_SIGNATUR_PRUEFEN` | `$31` | **`$09` CheckSignature** | `83 FF F1 31 09 02` |
| `FLASH_PROGRAMMIER_STATUS_LESEN` | `$31` | **`$0A`** | `82 FF F1 31 0A` |
| `FLASH_LOESCHEN` | `$31` | **`$02` ClearMemory** | `89 FF F1 31 02 00 00 00 06 00 00 00` |
| `FLASH_SCHREIBEN_ADRESSE` | **`$34` RequestDownload** | — | `89 FF F1 34 00 00 00 06 00 00 00 00` |
| `FLASH_SCHREIBEN` | **`$36` TransferData** | — | телетрамма собирается из данных |
| `FLASH_ZEITEN_LESEN` | `$22` ReadDataByCommonIdentifier | **ID `0x2501`** | `83 FF F1 22 25 01` |
| `FLASH_BLOCKLAENGE_LESEN` | `$22` | **ID `0x2506`** | `83 FF F1 22 25 06` |

`AUTHENTISIERUNG_START` — аргумент `BINAER_BUFFER`, в комментарии прямо:
*«Byte 21,…. : **Schluesseldaten**»* (ключевые данные), *«Byte 4 :
Authentisierungszeit in Sekunden»*.

`FLASH_LOESCHEN` — аргумент `BINAER_BUFFER` с полностью документированной
раскладкой (см. § 7).

---

## 4. `SPEICHERSEGMENT` — числовые коды сегментов памяти

Это то, что нужно для чтения защищённой области через `SPEICHER_LESEN`.

| `SEG_BYTE` | Имя | Смысл |
|---|---|---|
| `0x00` | `LAR` | linearAdressRange |
| `0x01` | `ROMI` | ROM/EPROM, внутренний |
| `0x02` | `ROMX` | ROM/EPROM, внешний |
| `0x03` | `NVRAM` | NV-RAM (характеристики, память DTC) |
| `0x04` | `RAMIS` | RAM внутренний (short MOV) |
| `0x05` | `RAMXX` | RAM внешний (x data MOV) |
| **`0x06`** | **`FLASH`** | **Flash EPROM, внутренний** |
| `0x07` | `UIFM` | User Info Field Memory |
| `0x08` | `VODM` | Vehicle Order Data Memory |
| **`0x09`** | **`FLASHX`** | **Flash EPROM, внешний** |
| `0x0B` | `RAMIL` | RAM внутренний (long MOV / регистры) |
| `0xFF` | `???` | неизвестный сегмент |

Джоб `SPEICHER_LESEN(SEGMENT, ADRESSE, ANZAHL)` — принимает **имя** сегмента
(строкой), сам достаёт `SEG_BYTE` через `tabget`, и проверяет `ADRESSE`
в диапазоне `0x000000–0xFFFFFF`, `ANZAHL` — 1…254.

**Практический вывод для H1:** чтобы прочитать `0xFFC000–0xFFFFFF`, нужно
вызвать `SPEICHER_LESEN` с `SEGMENT = "FLASH"` (код `0x06`), `ADRESSE =
0xFFC000`, `ANZAHL = 254`, в цикле.

**Симметрично для записи:** `SPEICHER_SCHREIBEN` — это `$3D`
WriteMemoryByAddress с теми же аргументами (`SEGMENT`, `ADRESSE`, `ANZAHL`,
данные), и он **не входит** в группу «Firmware/Flash» с challenge-response.
Если ЭБУ разрешает `$3D` в сегменте `FLASH`, задача решается вообще без
эксплойта. Проверять на донорском щитке и на заведомо безобидном адресе —
например, внутри NVRAM, — прежде чем пробовать FLASH.

---

## 5. `AUTHENTISIERUNG` — режим сообщает сам ЭБУ

Таблица `AUTHENTISIERUNG` в SGBD:

| `AUTH_NR` | Текст |
|---|---|
| `0x01` | `Simple` |
| `0x02` | `Symetrisch` |
| `0x03` | `Asymetrisch` |
| `0xFF` | `Keine` |

В конце `AUTHENTISIERUNG_ZUFALLSZAHL_LESEN` код делает
`tabseek "AUTH_NR"` → `ergs "AUTHENTISIERUNG", S1`, то есть **декодирует
полученный от ЭБУ байт в текст режима**.

**Это важный практический факт:** режим аутентификации не надо угадывать —
`$31 $07` возвращает и случайное число, и **тип аутентификации**. Один запрос
на живом щитке закрывает вопрос, какой из `Simple`/`Symetrisch`/`Asymmetrisch`
используется.

---

## 6. Два независимых диапазона подписи: PAF и DAF — обоснование H2

Таблица `PROGRAMMIERSTATUS` в SGBD:

| `SB` | Текст |
|---|---|
| `0x01` | Normalbetrieb |
| `0x03` | Speicher gelöscht |
| **`0x05`** | **Signaturprüfung PAF nicht durchgeführt** |
| **`0x06`** | **Signaturprüfung DAF nicht durchgeführt** |
| `0x07` | Programmprogrammiersitzung aktiv |
| `0x08` | Datenprogrammiersitzung aktiv |
| `0x0C` | Programm nicht vorhanden oder nicht vollständig |
| `0x0F` | Daten nicht vorhanden oder nicht vollständig |

Тот же набор повторяется в `RESULTCOMMENT` джоба `FLASH_LOESCHEN`
(«5 = Signaturpruefung PAF nicht durchgefuehrt»).

**PAF** = Programm-Austausch-Datei, **DAF** = Daten-Austausch-Datei. То есть
подписей **две**, и они раздельные — ровно как в MS45 (`Daten;64` /
`Programm;64`, см. § 10.1 основного плана). Джоб `FLASH_SIGNATUR_PRUEFEN`
принимает аргумент `BEREICH` со значениями **`'Programm'`** и **`'Daten'`**,
и в телетрамме передаёт `02` (для одного из них; разбор ветвления — в
`SGBD/disasm/FLASH_SIGNATUR_PRUEFEN.txt`).

Это усиливает **H2** (атака «непокрытый диапазон»): если проверяемых
диапазонов несколько и они задаются таблицей, вопрос «покрыта ли таблица
подписью» становится ключевым. Проверять надо оба диапазона по отдельности и
отдельно выяснить, что остаётся вне их.

---

## 7. Формат полезной нагрузки `BINAER_BUFFER` (из комментариев джобов)

Документирован прямо в SGBD для `FLASH_LOESCHEN` и `AUTHENTISIERUNG_START`:

```
Byte 0           : Datentyp (1:Daten, 2:Maskendaten)
Byte 1           : (unbenutzt) Wortbreite (1:Byte, 2:Word, 3:DWord)
Byte 2           : (unbenutzt) Byteordnung (0:LSB zuerst, 1:MSB zuerst)
Byte 3           : Adressierung (0: freie Adressierung, 1: Blockadressierung)
Byte 4           : Loeschzeit / Authentisierungszeit in Sekunden
Byte 5,6         : WordParameter 1 (low/high)
Byte 7,8         : WordParameter 2 (low/high)
Byte 9,10,11,12  : Maske (linksbuendig)
Byte 13,14       : Anzahl Bytedaten (low/high)
Byte 15,16       : Anzahl Wortdaten (low/high)
Byte 17,18,19,20 : Wortadresse (low/highbyte, low/highword)
Byte 21,....     : Flashdaten  /  Schluesseldaten
Byte 21+Anzahl   : ETX (0x03)
```

**Важно:** телетрамму собирает сам SGBD — приложение может не знать байтовую
упаковку, если вызывает джоб через EDIABAS/`api32`/`ediabasx`. Это аргумент
за то, чтобы на первом этапе (H1) не писать транспорт, а просто вызвать
`SPEICHER_LESEN`.

---

## 8. Диагностический концепт: D-CAN

Таблицы `KONZEPT_TABELLE` и `SG_DIAGNOSEKONZEPT`:

| `NR` | Концепт |
|---|---|
| **`0x10`** | **D-CAN** |
| `0x0F` | BMW-FAST |
| `0x0D` | KWP2000* |
| `0x0C` | KWP2000 |
| `0x06` | DS2 |

`SG_DIAGNOSEKONZEPT` выставляет ранг 1 для **BMW-FAST** — то есть для KOMBI
основной концепт BMW-FAST, а D-CAN доступен как `0x10`. Это согласуется с
выводом § 7 плана: на E9x после 2007 г. физика D-CAN, а кадрирование —
BMW-FAST. Выбор концепта делают джобы `DIAGNOSEPROTOKOLL_LESEN` /
`DIAGNOSEPROTOKOLL_SETZEN`.

---

## 9. Чего в SGBD **нет**: ключевого материала

Поиск по расшифрованному содержимому `KOMB87.prg` (1,28 МБ) по ключевым
словам `key`, `schluess`, `pabd`, `auth`, `signat`, `passw`, `rsa`, `md5`,
`secret`, `test` дал только:

* имена джобов и кодов ошибок (`ERROR_AUTHENTICATION`,
  `ERROR_SG_AUTHENTISIERUNG`, **`ERROR_TESTER_SERIAL_NR`**,
  `ERROR_FLASH_SIGNATURE_CHECK`);
* тайминги (`FLASH_AUTHENTISIERZEIT`, `FLASH_SIGNATURTESTZEIT`);
* `KEY1…KEY3`, `KEY10_KEY15` — это ключи сервисного интервала **CBS**, не криптография.

**Никаких `RSA`/`MD5`/`PABD` и никаких блобов ключей.** Скан всего файла на
окна по 64 байта с высокой энтропией и низкой печатностью не дал кандидатов.

При этом в `.ipo` (скрипт прошивки) есть строки:

```
, AUTHENTISIERUNG_START ( SG-Schluessel ...)     ← «ключ ЭБУ» передаётся в джоб
Authentisierungsart :
Key  : 
Schluessellaenge   
PABD-SG_AUTHENTISIERUNG
PABD-TestSchluesselAuthentisierung
```

**Вывод:** SGBD — это транспорт и протокол; он **не** содержит секрета.
Ключевой материал (или алгоритм его вывода) приходит от вызывающей стороны —
то есть из `.ipo`/WinKFP/ISTA, и для режима `Symetrisch` он обязан быть
восстановим. Для режима `Asymmetrisch` приватный ключ у BMW, и тогда остаётся
только обход.

`ERROR_TESTER_SERIAL_NR` — косвенное подтверждение, что в схеме участвует
**серийный номер тестера**, как и в документированной схеме MS45
(`MD5(userID ‖ serialNumber ‖ seed)`).

**Следующий шаг для этой ветки:** декодировать `.ipo` (формат CABI,
не BEST/1 — `decoderPrg.py` его не берёт, см. § 4.5 плана) и найти, откуда
берётся `SG-Schluessel` и что такое `PABD-TestSchluesselAuthentisierung`.

---

## 10. Что это меняет в плане

| Было | Стало |
|---|---|
| «Добыть `komb87.prg`» — пункт 1 критического списка | **выполнено**; пункт снят |
| «Коды сегментов `SPEICHER_*` неизвестны» | получены: `FLASH = 0x06`, `FLASHX = 0x09`, `LAR = 0x00` |
| «ID рутин `NG_*` неизвестны» | получены: `$31` → `02` ClearMemory, `07` RequestForAuthentication, `08` ReleaseAuthentication, `09` CheckSignature, `0A` статус |
| Режим аутентификации `SMA/SMB/SMC` — неясен | **ЭБУ сам сообщает режим** ответом на `$31 $07` |
| Подпись — «одна на всё» | **две раздельные: PAF (Programm) и DAF (Daten)** → H2 усиливается |
| Ключ искать в SGBD | **в SGBD его нет** (проверено); ветка ведёт в `.ipo` |

Итог: **H1 переходит из «надо разобраться» в «можно выполнять»** —
сегмент, адрес и джоб известны, осталось вызвать. H2 подтверждён структурно
(две подписи). H4/H6 требуют декодера `.ipo`.
