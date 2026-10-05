# Транспорт D-CAN для KOMBI (E9x, KOMB87): технический отчёт

Дата: 2026-10-05. Метод: чтение исходников (EdiabasLib C#, ediabasx TypeScript), официальной
документации EDIABAS (API Function Primer, BEST/2 user guide), первичных документов вендоров,
а также локальных артефактов проекта (`прошивки приборок/10flash.prg`, `080100HKOML2.ipo`,
`BimmerDaten`). Всё, что не подтверждено источником, помечено явно.

**Ключевой вывод, который меняет архитектуру:** в кабеле K+DCAN транспорт D-CAN/ISO-TP
реализован **в прошивке самого кабеля**, а не в хосте. Хост на PC (Windows/macOS/Linux) видит
обычный COM-порт и в режиме D-CAN отправляет по нему **ту же самую телеграмму BMW-FAST, что и
на K-линии**, только на скорости 115200 8N1. Это подтверждается кодом EdiabasLib: для концепта
`0x0110` (D-CAN) он ставит `baudRate = 115200`, `parity = None`, `ParTransmitFunc = TransBmwFast`
и пишет байты телеграммы прямо в `SerialPort` — никаких CAN-ID, ISO-TP и EDIC-заголовков при
этом не передаётся
([EdInterfaceObd.cs:828-845](https://github.com/uholeschak/ediabaslib/blob/master/EdiabasLib/EdiabasLib/EdInterfaceObd.cs#L828)).

Важное уточнение по формулировке из задания: класса `EdInterfaceDcan` в EdiabasLib **не
существует**. D-CAN — это «концепт» внутри `EdInterfaceObd.cs`; для «умных» адаптеров с
собственной прошивкой EdiabasLib CAN-обмен собран в `EdCustomAdapterCommon.CreateCanTelegram`
и в TS-порте `kdcan/telegram.ts`.

---

## 1. Байтовый формат обмена host ↔ кабель

### 1.1. Два разных класса кабелей — их надо различать (это подтверждено кодом)

| | «Умный» K+DCAN (UART-мост + MCU) | «Глупый» FTDI-паскар (dumb passthrough) |
|---|---|---|
| Детект | хост опрашивает кабель, получает `adapterType >= 0x0002` | опрос не отвечает |
| UART | **всегда 115200 8N1** (командный канал) | на скорости K-линии (9600/10400) |
| Что шлёт хост | телеграмму-обёртку с параметрами K-линии/CAN внутри | «сырую» телеграмму BMW-FAST |

Источник: `SerialInterface.ts` — ветка `isKDCanAdapter` держит порт на
`{ baudRate: 115200, dataBits: 8, parity: "none", stopBits: 1 }` и оборачивает каждую посылку в
adapter-telegram; ветка `else` (комментарий в коде: *«Dumb FTDI passthrough: drive the UART at
the K-line baud directly»*) настраивает порт на baud из CommParameter и включает DTR для
переключения направления полудуплексной K-линии
([SerialInterface.ts:677-720](https://github.com/emdzej/ediabasx/blob/main/packages/interface-serial/src/SerialInterface.ts#L677)).
Комментарий-шапка `adapterTransport.ts`: *«the PC always talks to the cable at 115200 8N1, and
each K-line transmission is wrapped by createAdapterTelegram(...)»*
([adapterTransport.ts:1-18](https://github.com/emdzej/ediabasx/blob/main/packages/interface-serial/src/kdcan/adapterTransport.ts#L1)).

### 1.2. Телеграмма BMW-FAST (то, что реально уходит в кабель в режиме D-CAN)

Формат — ISO 14230-подобный с адресной информацией, контрольная сумма — **8-битная СУММА**
(не XOR!):

```
короткая форма (данные <= 0x3F байт):
  [0x80 | len] [TGT] [SRC] [data ...] [sum8]

длинная форма (данные > 0x3F байт):
  [0x80] [TGT] [SRC] [len_lo] [data ...] [sum8]
  (если len >= 0x100: [0x80] [TGT] [SRC] [0x00] [len_hi] [len_lo] [data...] [sum8])
```

* `TGT` — диагностический адрес ЭБУ (в SGBD стоит заглушка `$FF`, EDIABAS подставляет значение).
* `SRC` — адрес тестера, для BMW-FAST это **`0xF1`** (подтверждено: в `SerialInterface.ts`
  `testerAddress ?? 0xf1`, `ecuAddress ?? 0x12`).
* `sum8` — `CalcChecksumBmwFast` = сумма всех предыдущих байт по модулю 256
  ([EdInterfaceBase.cs:933-941](https://github.com/uholeschak/ediabaslib/blob/master/EdiabasLib/EdiabasLib/EdInterfaceBase.cs#L933),
  [checksum.ts](https://github.com/emdzej/ediabasx/blob/main/packages/interface-serial/src/kdcan/checksum.ts)).
* Разбор длины ответа — `TelLengthBmwFast` / `getBmwFastDataWindow`
  ([EdInterfaceBase.cs:881-931](https://github.com/uholeschak/ediabaslib/blob/master/EdiabasLib/EdiabasLib/EdInterfaceBase.cs#L881)).

Готовый конструктор телеграммы (портируется в Python 1:1) —
[kwp2000.ts:189-221](https://github.com/emdzej/ediabasx/blob/main/packages/interface-serial/src/kdcan/kwp2000.ts#L189).

Пример: чтение топлива у KOMBI (`STATUS_TANKINHALT` → `$21 $0A`), SGBD-телеграмма `82 FF F1 21 0A`.
С подставленным адресом ЭБУ `A` и суммой:

```
82 A F1 21 0A sum     где sum = (0x82+A+0xF1+0x21+0x0A) & 0xFF
```

Это независимо подтверждено локальным разбором SP-Daten в самом проекте
(`bmw-e90-can-display/docs/diag-jobs.md`, разбор `.prg` через `BimmerDaten/decoderPrg.py`).

### 1.3. Обёртка «умного» адаптера: параметры K-линии (telType 0x00 / 0x02)

Заголовок `00 <telType> ...`; `telType` зависит от версии прошивки адаптера
(`< 0x0008` → `0x00`, иначе `0x02`):

```
telType 0x00 (9 байт заголовка):
  [0]=0x00 [1]=0x00 [2..3]=baud/2 (big endian) [4]=flags1
  [5]=interByteTime [6..7]=len (big endian) [8..]=data  [last]=sum8
telType 0x02 (11 байт заголовка):
  [0]=0x00 [1]=0x02 [2..3]=baud/2 [4]=flags1
  [5]=flags2 [6]=interByteTime [7]=KWP1281 timeout(60)
  [8..9]=len (big endian) [10..]=data [last]=sum8
```

`flags1` (константы `KLINEF1_*`): `0x07` маска чётности (`0=none,1=even,2=odd,3=mark,4=space`),
`0x08` использовать L-линию, `0x10` послать pulse, `0x20` **no echo**, `0x40` fast init,
`0x80` использовать K-линию. `flags2`: `0x01` KWP1281-detect.

Источник:
[telegram.ts:85-169](https://github.com/emdzej/ediabasx/blob/main/packages/interface-serial/src/kdcan/telegram.ts#L85)
и его C#-первоисточник
[EdCustomAdapterCommon.cs](https://github.com/uholeschak/ediabaslib/blob/master/EdiabasLib/EdiabasLib/EdCustomAdapterCommon.cs).

### 1.4. Обёртка «умного» адаптера: CAN-телеграмма (telType 0x01 / 0x03)

Это формат для адаптеров с явным CAN-API (Deep OBD / ESP32 / ELM327-replacement):

```
[0]=0x00 [1]=telType(0x01 при ver<0x0009, иначе 0x03)
[2]=protocol (0x00 BMW, 0x01 TP20, 0x02 ISO-TP)
[3]=baud index (0x01 = 500 kbit/s, 0x09 = 100 kbit/s)
[4]=flags (0x01 NO_ECHO, 0x02 CAN_ERROR, 0x04 CONNECT_CHECK, 0x08 DISCONNECT)
TP20:  [5]=0x0f [6]=0x0a [7]=100 (1000/10)
ISOTP: [5]=0x00 [6]=0x00 [7..8]=canTxId [9..10]=canRxId
telType 0x01: [8..9]=len  [10..]=data   [last]=sum8
telType 0x03: [11..12]=len [13..]=data  [last]=sum8
```

Источник:
[telegram.ts:265-345](https://github.com/emdzej/ediabasx/blob/main/packages/interface-serial/src/kdcan/telegram.ts#L265).

### 1.5. Команды опроса/инициализации адаптера (то, что реально уходит в кабель)

Опрос идёт **телеграммами BMW-FAST на «виртуальный ЭБУ» с адресом `0xF1`**; кабель отвечает
сначала **эхом своей же посылки**, затем payload'ом с суммой:

| Команда (hex) | Ответ | Что возвращает |
|---|---|---|
| `82 F1 F1 FE FE sum` | 6 б. | `resp[4]` = статус зажигания |
| `84 F1 F1 06 (mode^0x55) (0xFF^0x55) (0x80^0x55) sum` | 8 б. | escape/conf: чтение/запись, `mode` XOR 0x55 |
| `82 F1 F1 FD FD sum` | 9 б. | `resp[4..5]` = adapterType (BE), `resp[6..7]` = adapterVersion (BE) |
| `82 F1 F1 FB FB sum` | 13 б. | `resp[4..11]` = серийный номер (8 байт) |
| `82 F1 F1 FC FC sum` | 6 б. | `resp[4]` = напряжение адаптера ×0.1 В |

Источник:
[adapterInfo.ts:85-244](https://github.com/emdzej/ediabasx/blob/main/packages/interface-serial/src/kdcan/adapterInfo.ts#L85).
`adapterType >= 0x0002` = «умный» адаптер; CAN-телеграммы поддержаны с `adapterVersion >= 0x0008`
(ISO-TP — с `>= 0x0009`).

### 1.6. Инициализация в D-CAN режим

Отдельной «магической» последовательности входа в D-CAN нет. Практически:

1. Открыть порт **115200 8N1**, `parity=None`, `stopBits=1`, `dataBits=8`
   ([dcan.ts:29-41](https://github.com/emdzej/ediabasx/blob/main/packages/interface-serial/src/kdcan/dcan.ts#L29)).
2. Поднять `DTR` и `RTS` (в TS: `setDtr(true)`/`setRts(true)`); для «умного» адаптера линии
   направления кодируются флагами телеграммы, а не реальным DTR.
3. Послать телеграмму BMW-FAST с `TGT` = адрес ЭБУ. Кабель сам сформирует кадры CAN.
4. Для K-линии в «умном» режиме — сначала записать baud/parity/флаги через adapter-telegram;
   fast-init передаётся флагом `KLINEF1_FAST_INIT (0x40)` или pulse-телеграммой.

Для F-серии: если в кабеле оставлен pin 8, он конфликтует с активацией Ethernet — вендор
рекомендует его выпаять (см. §1.8).

### 1.7. Эхо, DLC, sequence numbers

* **Эхо**: у «умного» адаптера эхо своей посылки возвращается перед ответом; хост обязан его
  прочитать и сверить байт-в-байт (`HasAdapterEcho`; в `TransKwp2000` — сверка эха и ошибка
  `EDIABAS_IFH_0003` при несовпадении). Флаг `KLINEF1_NO_ECHO (0x20)` / `CANF_NO_ECHO (0x01)`
  позволяет попросить адаптер эхо не присылать
  ([EdInterfaceObd.cs](https://github.com/uholeschak/ediabaslib/blob/master/EdiabasLib/EdiabasLib/EdInterfaceObd.cs)).
* **DLC**: кадры CAN всегда 8 байт, «хвост» добивается `0x00` (см. построение `canSendBuffer`).
* **Sequence numbers**: PCI consecutive-frame `0x2N`, `N` инкрементируется 1…15 с переносом в 0;
  в C#-коде есть отдельный счётчик `blockCount` и обработка `BlockSize`/`SeparationTime` из
  flow-control кадра
  ([EdElmInterface.cs:595-705](https://github.com/uholeschak/ediabaslib/blob/master/EdiabasLib/EdiabasLib/EdElmInterface.cs#L595)).

### 1.8. Аппаратура кабеля

* USB-UART-мосты, встречающиеся в K+DCAN-кабелях: **FT232RL/FT232RQ `0403:6001`** (рекомендуется),
  **CH340/CH341 `1A86:7523`**, **CP2102 `10C4:EA60`** — таблица чипсетов в README проекта
  QFLASH21 ([QFLASH21 README](https://github.com/batko15/QFLASH21)).
* Разбор «классического» кабеля: FT232RL + стабилизатор L7805 (и, судя по всему, MCU) — на фото
  teardown'а видно только FT232 и L7805; **точная модель MCU достоверно не подтверждена**
  ([auto-diagnosis.org](http://www.auto-diagnosis.org/warning-for-bad-kdcan-cable/)).
  Русскоязычный источник утверждает «собран на чипах Atmega162, FTDI», но это не первичный
  источник — **не подтверждено**.
* Вендор (Jephis Technology / one-stop-electronics) пишет: обязательно выставить **latency timer
  FTDI с 16 мс на 1 мс**, иначе связь таймаутит; pin 8 удаляется для F-серии; pin 7 — первичная
  K-line, pin 8 — вторичная K-line
  ([APN_Connection_Stability.pdf](https://www.one-stop-electronics.com/wp-content/uploads/2023/05/APN_Connection_Stability.pdf)).
* Распиновка OBD-II разъёма BMW: `4` — силовая масса, `5` — сигнальная масса, `6` — CAN-H,
  `14` — CAN-L, `7` — K-line (primary), `8` — K-line (secondary; на F-серии — активация
  Ethernet), `16` — +12 В. Переключатель на кабеле выбирает, куда идёт K-line: pin 7 или pin 8;
  на D-CAN это не влияет (CAN всегда на 6/14) — [UOBDII](http://blog.uobdii.com/kdcan-cable-with-switch-pin-78-good-or-not/).
* Для FT232 есть отдельная тема про настройки EEPROM кабелей K+D CAN
  ([e46fanatics](https://www.e46fanatics.com/threads/ft232-eeprom-settings-k-d-can-cables.1097604/)).

---

## 2. Готовые реализации host-стороны

### 2.1. EdiabasLib (эталон)

* URL: <https://github.com/uholeschak/ediabaslib> · язык **C# / .NET** · лицензия **GPL-3.0**
  (важно: GPL-3 распространяется на производные — для закрытого продукта это блокер).
* Файлы, которые надо читать:
  * [EdInterfaceObd.cs](https://github.com/uholeschak/ediabaslib/blob/master/EdiabasLib/EdiabasLib/EdInterfaceObd.cs) —
    всё ядро: концепты протоколов (`case 0x010C/0x010F/0x0110`), `TransKwp2000`, `TransDs2`,
    `TransKwp2000S`, эхо, тайминги `ParTimeoutStd/ParRegenTime/ParTimeoutTelEnd/ParInterbyteTime`,
    `ParTimeoutNr78/ParRetryNr78`, `ParTesterPresentTime/ParTesterPresentTel`,
    EDIC-параметры (`ParEdicTesterCanId`, `ParEdicEcuCanId`, наборы `0x0001/0x0002/0x0004/0x0091`).
  * [EdInterfaceEdic.cs](https://github.com/uholeschak/ediabaslib/blob/master/EdiabasLib/EdiabasLib/EdInterfaceEdic.cs) —
    наследник `EdInterfaceObd` (`Interface = EDIC`, свойство `EdicComPort`).
  * [EdCustomAdapterCommon.cs](https://github.com/uholeschak/ediabaslib/blob/master/EdiabasLib/EdiabasLib/EdCustomAdapterCommon.cs) —
    `CreateCanTelegram`, `CalcChecksumBmwFast`, `InterfaceSetCanIds`, константы `CAN_PROT_BMW/TP20/ISOTP`.
  * [EdElmInterface.cs](https://github.com/uholeschak/ediabaslib/blob/master/EdiabasLib/EdiabasLib/EdElmInterface.cs) —
    самая наглядная реализация D-CAN «в лоб» через ELM327: `ATSH6F1`, `ATFCSH6F1`,
    `ATFCSD30<addr>0000`, `ATCEA<addr>`, `ATFCSM1`, `ATMA`, и разбор ответов по ID.
  * [EdInterfaceBase.cs](https://github.com/uholeschak/ediabaslib/blob/master/EdiabasLib/EdiabasLib/EdInterfaceBase.cs) —
    `TelLengthBmwFast`, `DataLengthBmwFast`, `CalcChecksumBmwFast`.
  * `EdiabasNet.cs` — интерпретатор BEST/2 (исполняет SGBD), `apiNET`/`Api32` — совместимый
    `api32.dll`.
* Настройки: [docs/EdiabasLib.config_file.md](https://github.com/uholeschak/ediabaslib/blob/master/docs/EdiabasLib.config_file.md)
  — `Interface = STD:OBD | ADS | ENET | RPLUS | EDIC`, `ObdComPort`, `ApiTrace`, `IfhTrace`,
  `TracePath`, `EcuPath`, `RetryComm`; для Android FTDI — `FTDI:<serial>`.
* Поддержка адаптеров: [docs/AdapterTypes.md](https://github.com/uholeschak/ediabaslib/blob/master/docs/AdapterTypes.md)
  — «FTDI USB: BMW-DS2 Yes, BMW-FAST Yes, BMW-FAST-ENET **D-CAN**»; отдельно предупреждение про
  поддельные FT232R.
* Ключевое техническое ограничение для нас: в EdiabasLib `EdFtdiInterface` (D2XX/bitbang) собирается
  **только под `#if ANDROID`**; на PC кабель используется как обычный COM-порт
  ([EdInterfaceObd.cs:1493-1522](https://github.com/uholeschak/ediabaslib/blob/master/EdiabasLib/EdiabasLib/EdInterfaceObd.cs#L1493)).
* Переиспользование из Python: **напрямую — нет**. Варианты: sidecar-процесс на .NET + JSON-RPC;
  `pythonnet`; либо `api32.dll`-эмуляция из EdiabasLib (тогда host-сторона — родной `api32`).

### 2.2. emdzej/ediabasx (самый удобный источник для порта на Python)

* URL: <https://github.com/emdzej/ediabasx> · язык **TypeScript/C11** · лицензия: **NOASSERTION**
  (в репозитории есть `LICENSE`, но SPDX не определён — надо проверить перед переиспользованием).
* Что внутри ценного:
  * `packages/interface-serial/src/kdcan/*` — **полная, чистая реализация**: `constants.ts`
    (все флаги), `checksum.ts`, `telegram.ts` (все три типа телеграмм), `adapterInfo.ts` (опрос
    кабеля), `adapterTransport.ts` (обёртка), `kwp2000.ts` (BMW-FAST + таймеры + NR78),
    `fastInit.ts`, `slowInit.ts`, `ds2.ts`, `dcan.ts`, `lineControl.ts`.
  * `packages/protocol-kwp`, `packages/protocol-uds` (ISO-TP-сегментация: `segmentIsoTpPayload`,
    `parseIsoTpFrame`).
  * `packages/interpreter` — VM BEST/2 (порт `EdiabasNet`), `packages/best-parser`,
    `packages/best-decompiler`.
  * `reference/` — **декомпилированные заголовки BMW-шных DLL** (`api32.dll.c/h`, `OBD32.dll.c/h`,
    `ebas32.dll.c/h`, `XStd32`, `XEnet32`, `XNul32`) — первичный материал по транспорту.
  * `docs/interfaces/obd32-protocols.md`, `obd32-analysis.md`, `xstd32-analysis.md` — разбор
    протоколов OBD32 (K-линия: DS2/KWP2000/ISO9141), полезно как эталон таймингов и концептов.
  * `packages/ediabas/src/config-schema.ts` — практичная схема конфига:
    `protocol: 'kline'|'dcan'|'isotp'|'tp20'`, `testerAddress`, **`ecuAddress`**,
    `testerCanId`, `ecuCanId`, `baudRate` (default 9600), `parity`.
* Переиспользование из Python: кода нет, но это **лучшая спецификация для порта**; кроме того
  ediabasx умеет поднимать JSON-RPC-сервер (`ediabasx serve`) и gateway — можно вызывать из Python
  как внешний процесс.

### 2.3. pydiabas (Python + EDIABAS)

* URL: <https://github.com/BembelBytes/pydiabas> · PyPI: `pip install pydiabas` · **Python, MIT**.
* Что делает: `ctypes`-обёртка `api32.dll` (`WinDLL(find_library("api32"))`), экспортирует
  `apiInit/apiInitExt/apiEnd/apiJob/apiJobData/apiJobExt/apiResultBinary/apiResultText/...`
  (в коде используются имена с двойным подчёркиванием: `_api32.__apiInit`, `_api32.__apiJob` —
  так в `api.h` объявлены реальные экспорты).
  Файлы: [`src/pydiabas/ediabas/api32.py`](https://github.com/BembelBytes/pydiabas/blob/main/src/pydiabas/ediabas/api32.py),
  [`statics.py`](https://github.com/BembelBytes/pydiabas/blob/main/src/pydiabas/ediabas/statics.py)
  (типы `API_BINARY = c_ubyte`, `API_MAX_PARA = 1024`, `API_MAX_PARAEXT = 65536`, коды ошибок
  `EDIABAS_ERROR.IFH_00xx`).
* **Критично**: требуется **32-битный Python** (адреса `api32.dll`) и Windows + установленный
  EDIABAS ≥ 7.0. Автор тестировал на Python 3.12/3.14 **32-bit**. Это готовый кандидат для
  варианта (c).

### 2.4. garagediag (Python, K+DCAN по serial)

* URL: <https://github.com/tooming/garagediag> · **Python**, лицензия в репо есть (файл LICENSE).
* `ds2_diag.py`: DS2 на K-линии **9600 8E1** (even parity!), кадр `[ecu_addr, total_len, data...,
  XOR]`, XOR-чек-сумма, retry, таймауты.
* `kline_obd.py`: эталон «сырого» доступа через `termios`/`fcntl` + `IOSSIOSPEED`, fast-init через
  `TIOCSBRK`/`TIOCCBRK` (25 мс low, 25 мс high), телеграмма `C1 33 F1 81` + сумма, съём эха
  (`if resp.startswith(msg): resp = resp[len(msg):]`).
* `isotp.py`: **чистая реализация ISO-TP на Python** (SF/FF/CF/FC, extended addressing, ожидание
  flow-control, `bs`/`stmin`, до 4095 байт) — прямо переиспользуемо, если строить CAN-слой самому.
* K-линия, D-CAN не реализован.

### 2.5. Прочие (кратко)

| Проект | Язык / лицензия | Что реализует | Из Python |
|---|---|---|---|
| [kmalinich/node-bmw-client](https://github.com/kmalinich/node-bmw-client) | JS, MIT | E38…E9x, DS2/ibus/D-CAN через serial-обёртки, 187★ | только как референс |
| [ilicmiljan/open-can-controller](https://github.com/ilicmiljan/open-can-controller) | C, GPL | открытый CAN-контроллер **для приборок E9X** (прошивка+плата) | как референс/железо |
| [batko15/QFLASH21](https://github.com/batko15/QFLASH21) | TS + Android/Java, — | **реальная прошивка BMW** (DDE4/EDC15) по K-линии/KWP2000 из браузера; таблица чипсетов кабелей; 5-baud init, echo, 0x78-pending | референс |
| [jakka351/OpenJ2534](https://github.com/jakka351/OpenJ2534) | C/разное | ресурсы J2534 PassThru (DLL, примеры) | через ctypes — возможно, но для BMW D-CAN нужен BMW-специфичный PassThru-драйвер |
| ediabasx `packages/interface-j2534` | TS | PassThru через **Tactrix OpenPort 2.0** | референс |
| [pylessard/python-can-isotp](https://github.com/pylessard/python-can-isotp) | Python, **MIT** | ISO-TP (ISO 15765-2) поверх произвольной шины (`can-isotp`, v2.0.7) | **требует CAN-интерфейс**; K+DCAN ≠ SocketCAN |
| [pylessard/python-udsoncan](https://github.com/pylessard/python-udsoncan) | Python, **MIT** | UDS (ISO 14229), v1.26.1 | требует `can-isotp` → CAN-шину |
| [python-can](https://pypi.org/project/python-can/) | Python | драйверы CAN (socketcan, pcan, vector…) | **K+DCAN не поддерживается** |
| `pyserial` 3.5 | Python, BSD | serial | нужен |
| `bimmer_connected` | Python | облако BMW ConnectedDrive (F/G, EV) | **не относится** к D-CAN/KWP2000 |
| BimmerCode/BimmerLink, xHP | закрытые | внутри — ELM327-подобный/свой транспорт | не переиспользуемо |
| Deep OBD ([uholeschak](https://github.com/uholeschak/ediabaslib)) | Java, GPL-3.0 | Android-приложение на EdiabasLib + своя прошивка адаптеров | референс |

**Не найдено:** ни одного PyPI-пакета, который реализует именно host-сторону BMW D-CAN/K+DCAN.
`pydiabas` — единственный реально пригодный «Python + BMW D-CAN» пакет, и он работает **не через
serial, а через `api32.dll`** (то есть это не свой транспорт, а обёртка над EDIABAS).

---

## 3. D-CAN / K-CAN / PT-CAN

### 3.1. Скорости и шины

* **D-CAN** (диагностическая CAN на пинах 6/14 разъёма OBD-II) — **500 kbit/s**, ISO 11898-2.
* **PT-CAN** (силовой агрегат) — **500 kbit/s**.
* **K-CAN** (кузов, приборка, комфорт) — **100 kbit/s**, low-speed/fault-tolerant.
* UART до кабеля в D-CAN режиме — **115200 8N1**; 500 kbit/s — это уже шина CAN, а не serial.

Приборка KOMBI в E9x сидит на **K-CAN**; диагностические запросы с колодки OBD доходят до неё
через центральный шлюз (CAS/JBE). Это ровно то, что уже зафиксировано в локальном
`bmw-e90-can-display/docs/diag-jobs.md`. Точная схема маршрутизации шлюзом по первичным
документам не подтверждена, но практическое следствие подтверждено всей экосистемой
(INPA/Tool32/NCS Expert читают KOMBI через OBD).

### 3.2. CAN-ID (подтверждено кодом EdiabasLib)

Формула: **ID = 0x600 | <адрес источника>**.

* Запрос тестера: `sourceAddr = 0xF1` → **ID запроса `0x6F1`** всегда, независимо от того, к
  какому ЭБУ обращаемся.
  Код: `int canHeader = 0x600 | sourceAddr;` → `ATSH6F1`
  ([EdElmInterface.cs:505-508](https://github.com/uholeschak/ediabaslib/blob/master/EdiabasLib/EdiabasLib/EdElmInterface.cs#L505)).
* Ответ ЭБУ: **ID = `0x600 | адрес_ЭБУ`**, и его младший байт равен адресу ЭБУ. Проверка в
  приёмнике flow-control кадра:
  `((canRecData[0] & 0xFF00) == 0x0600) && ((canRecData[0] & 0xFF) == targetAddr)`
  ([EdElmInterface.cs:628-632](https://github.com/uholeschak/ediabaslib/blob/master/EdiabasLib/EdiabasLib/EdElmInterface.cs#L628)).
  Пример: адрес ЭБУ `0x12` (DME/DDE) → запрос `0x6F1`, ответ `0x612`.
* **Адрес ЭБУ передаётся внутри кадра** — это ISO-TP **extended addressing**: первый байт
  полезной нагрузки = адрес получателя, второй = PCI.
  ```
  запрос:  ID 0x6F1  | [TGT] [0x0N] [KWP2000 payload ...] [00..]   (DLC=8)
  ответ:   ID 0x600|A| [0xF1] [0x0N] [payload ...]                  (DLC=8)
  ```
  Именно так строит кадры C#: `canSendBuffer[0] = targetAddr; canSendBuffer[1] = 0x00|len;`
  ([EdElmInterface.cs:585-593](https://github.com/uholeschak/ediabaslib/blob/master/EdiabasLib/EdiabasLib/EdElmInterface.cs#L585)).
* PCI: `0x0N` single frame, `0x1N` first frame (12-битная длина), `0x2N` consecutive,
  `0x3N` flow control (`0x30` CTS / `0x31` wait / `0x32` overflow).
* Про `0x6F0`/`0x7DF` (функциональный broadcast): в коде EdiabasLib функционального ID для BMW
  D-CAN **не найдено** — используется только `0x6F1` с адресом получателя в payload.
  `0x7DF` — это generic OBD-II функциональный ID, к BMW-специфичным job'ам KOMB87 отношения не
  имеет. **Не подтверждено**, что KOMB87 отвечает на `0x7DF`.

### 3.3. Чем D-CAN отличается от K-line/DS2

| | DS2 (K-line) | KWP2000/BMW-FAST (K-line) | D-CAN |
|---|---|---|---|
| Физика | K-line, 1 провод | K-line | CAN-H/L, витая пара |
| Скорость | 9600 8E1 | 10400 (или 9600) 8N1 | 500 kbit/s |
| Кадр | `[addr][len][data...][XOR]` | `[0x80|len][TGT][SRC][data...][sum8]` | ISO-TP по CAN, ID 0x6F1 / 0x600\|A |
| Чек-сумма | XOR | 8-битная сумма | нет (CRC CAN) |
| Init | 5-baud wake address | fast init (25 мс low) / 5-baud | нет, шина постоянно активна |

### 3.4. Как хост выбирает протокол

* «Концепт» приходит из SGBD: таблицы **`KONZEPT_TABELLE`** / **`SG_DiagnoseKonzept`**.
  Проверено на локальном `d60m47a0_dcan.prg` из EdiabasLib — там есть строки `KONZEPT_TABELLE`,
  `SG_DiagnoseKonzept`, `KONZEPT_TEXT`, `INTERFACE_TYP`, а также таблица адресов ЭБУ
  `ECU_ADR_WERT`, `ECU_ADR_HEX`, `ECU_ADR_TEXT` со значениями `DME/DDE`, `Kombi`, `DME/DDE_slave`,
  `nicht erlaubt`.
* Числовые концепты в коде EdiabasLib:

  | Концепт | Hex | Что это | Скорость serial |
  |---|---|---|---|
  | BMW-FAST | `0x010C` / `0x010F` | KWP2000 на K-line (fast init) | из `CommParameter[1]` (9600/10400), parity None |
  | **D-CAN** | **`0x0110`** | CAN-диагностика | **жёстко 115200**, parity None, `TransBmwFast` |
  | ISO 9141/OBD | `0x0101`? | DS2/ISO | Even parity |

  ([EdInterfaceObd.cs:788-845](https://github.com/uholeschak/ediabaslib/blob/master/EdiabasLib/EdiabasLib/EdInterfaceObd.cs#L788)).
  Для `0x0110` требуется `CommParameter.Length >= 30`; таймауты берутся из
  `CommParameter[7..10]` (`ParTimeoutStd`, `ParRegenTime`, `ParTimeoutNr78`, `ParRetryNr78`),
  `ParTimeoutTelEnd = 10`.
* SGBD-джобы выбора протокола (подтверждено локально): **`DIAGNOSEPROTOKOLL_LESEN`** →
  результаты `DIAG_PROT_ANZAHL`, `DIAG_PROT_NR`; **`DIAGNOSEPROTOKOLL_SETZEN`** (аргумент
  `DIAG_PROT`). В flash-скрипте INPA они вызываются как `GET_DIAG_PROT` / `SET_DIAG_PROT`
  (функции `GetDiagProt()` / `SetDiagProt()`).
* В API EDIABAS это же доступно через `apiSetConfig("Interface", ...)` и SGBD-джобы; в
  `EdInterfaceObd.TransmitData` видел команды `CommAnswerLenProtected[1]`: `0x0001` (param set 1),
  `0x0002` (wake address), `0x0004` (**EDIC CAN**: wake/tester/ECU адреса + `KeyBytes = DA 8F
  <wake> 54 50`), `0x0091` (**EDIC ISO-TP**: `canTxId`/`canRxId`, P2/P2ext), `0x0010` start comm,
  `0x0011` stop comm, `0x0082` normal comm, `0x0084` stop frequent
  ([EdInterfaceObd.cs:1700-1849](https://github.com/uholeschak/ediabaslib/blob/master/EdiabasLib/EdiabasLib/EdInterfaceObd.cs#L1700)).

---

## 4. Практика: реалистично ли сделать это на Python

### 4.1. Да, реалистично — но объём работ зависит от кабеля

* **Если кабель «умный» (в нём есть MCU):** свой D-CAN/ISO-TP **не нужен вообще**. Python должен
  уметь ровно две вещи: (1) serial 115200 8N1 и (2) сборку/разбор телеграммы BMW-FAST с суммой.
  Это примерно 300–400 строк. Именно так работает EdiabasLib на PC.
* **Если кабель «умной» прошивки EdiabasLib (Deep OBD/ESP32):** нужен CAN-путь через
  adapter-telegram (telType `0x03`, ISO-TP, `canTxId=0x6F1`, `canRxId=0x600|A`) — то есть
  нужен ISO-TP в Python (`garagediag/isotp.py` — готовый каркас).
* **Если это просто CAN-интерфейс** (SocketCAN/PCAN/Tactrix J2534) — тогда `python-can` +
  `can-isotp` + свой тонкий слой BMW-адресации.

### 4.2. Подводные камни (все подтверждены кодом)

1. **TesterPresent (`0x3E`)**: обязателен, иначе ЭБУ выйдет из диагностической сессии. В
   EDIABAS/EdiabasLib он параметризуется SGBD'ом: `ParTesterPresentTime` (интервал, мс) и
   `ParTesterPresentTel`/`ParTesterPresentTelLen` (сами байты телеграммы, обычно `3E`/`3E 80`).
   Для D-CAN через EDIC-набор 4 интервал берётся из `CommParameter[60..61]`, телеграмма — из
   `CommParameter[49..]`; для ISO-TP-набора `0x0091` — интервал `[72..73]`, телеграмма `[77..]`
   ([EdInterfaceObd.cs:1724-1736, 1809-1821](https://github.com/uholeschak/ediabaslib/blob/master/EdiabasLib/EdiabasLib/EdInterfaceObd.cs#L1724)).
   Фоновый поток `StartCommThread()` шлёт его сам. В INPA flash-скрипте этому соответствуют
   вызовы `TesterPresentHandling()` / `StopTesterPresentHandling()` — то есть **во время прошивки
   tester-present управляется явно**.
2. **Тайминги**: `P1` (межбайтовый/telegram-end), `P2` (ответ, по умолчанию в SGBD), `P2*` при
   `0x78`, `P3` (regen time между запросами), `W1..W5` при инициализации. В TS-реализации
   значения по умолчанию: `w1=300, w2=20, w3=20, w4=50, w5=300, p1=10, p2=1200, p3=20, p4=0,
   timeoutNr78=5000, retryNr78=2`
   ([kwp2000.ts:5-19](https://github.com/emdzej/ediabasx/blob/main/packages/interface-serial/src/kdcan/kwp2000.ts#L5)).
3. **NR78 (0x78 = «response pending»)**: ответ `7F <svc> 78` продлевает ожидание до
   `ParTimeoutNr78`; надо НЕ считать это финальным ответом и повторить чтение (та же логика в
   C#: `ParTimeoutNr78`/`ParRetryNr78`). Для прошивки это критично — стирание флеша отдаёт
   `0x78` и `RoutineNotComplete`.
4. **Эхо**: у «умного» кабеля читать и сверять эхо, иначе весь разбор ответа сдвинется.
   У «глупого» — эхо на проводе K-line снимается сравнением с отправленным.
5. **Направление линии (DTR)**: для полудуплексной K-line нужен DTR во время передачи
   (`ParSendSetDtr`); для «умного» кабеля — наоборот, DTR не нужен, направление внутри
   телеграммы (`ParSendSetDtr = !HasAdapterEcho`).
6. **FTDI latency timer = 1 мс** — иначе таймауты.
7. **Потокобезопасность**: и приём ответов, и tester-present живут в отдельном потоке; в Python —
   `threading` + `serial` с аккуратной блокировкой.
8. **Не путать чек-суммы**: BMW-FAST/адаптер — сумма; DS2/KWP1281 — XOR (`CalcChecksumXor`).

### 4.3. PyPI и EDIABAS как бэкенд

* PyPI: готового транспорта BMW D-CAN **нет** (см. §2.5). `can-isotp`/`udsoncan` требуют CAN-шину;
  K+DCAN в `python-can` не поддержан. `pyserial` + своя телеграмма — рабочий путь.
* EDIABAS как бэкенд — **самый надёжный путь для прошивки**, официально документирован:
  * `APIBOOL apiInit(void)`, `APIBOOL apiInitExt(const char *ifh, const char *deviceUnit,
    const char *deviceApplication, const char *reserved)` — `ifh` = интерфейсный handler
    (например `STD:OBD`, `EDIC`, `ENET`).
  * `void apiJob(char *ecu, char *job, char *para, char *result)` — **асинхронный**: `ecu` —
    имя `.prg`, иначе `.grp`; параметры через `;`; опросить `apiState()` до READY, затем
    `apiResult*()`.
  * `void apiJobData(char *ecu, char *job, unsigned char *parabuf, int *paralen, char *result)` —
    для бинарных параметров (нужно для записи флеша).
  * `apiSetConfig(const char *config, const char *value)` / `apiGetConfig`, `apiErrorCode`,
    `apiErrorText`, `apiResultText`, `apiResultBinary`, `apiResultNumber/Name/Format`, `apiResultsNew/Scope/Delete`,
    `apiBreak`, `apiEnd`.
  * Типы/лимиты: `API_BINARY = unsigned char`, `API_MAX_PARA = 1024`, `API_MAX_PARAEXT = 65536`,
    `API_MAX_BINARYEXT = 65536`.
  * Источник: **EDIABAS API Function Primer** — [apiref.pdf](http://obdrus.ru/f/apiref.pdf)
    (зеркало официального документа), и [BEST/2 user guide](http://obdrus.ru/d/787731/d/bestuser.pdf)
    (описание `.prg`/`.grp`, `INITIALISIERUNG`, `EcuPath` в `EDIABAS.INI`).
  * Готовая обёртка из Python — `pydiabas` (MIT), **32-битный Python**, Windows.
  * Tool32: командный batch-режим документированно **не найден**; есть «Testrun» на `.tst`-файлах,
    которые должны лежать в ECU-каталоге
    ([Tool32 news](https://git.0x45.cz/em/bmw-advanced-tools/raw/commit/f743fd5cb15e787da7404f2a0b2d1797af79f8ad/app/EDIABAS/Bin/Tool32_News_EN.pdf)),
    и репозиторий-зеркало Standard Tools —
    [git.0x45.cz/em/bmw-advanced-tools](https://git.0x45.cz/em/bmw-advanced-tools). Вывод: shell-out
    в Tool32 ненадёжен, надо использовать `api32.dll` (вариант c) или .NET-sidecar (вариант b).

---

## 5. Прошивка через D-CAN

### 5.1. Что удалось установить точно (локальные первичные артефакты)

В проекте уже лежат `прошивки приборок/10flash.prg` (заголовок `@EDIABAS OBJECT`, SGBD с именем
**`FLASH`**, сборка из `FLASH.B2V`) и `080100HKOML2.ipo` — INPA-скрипт прошивки приборки HKOML2.
Из него извлекается **полный порядок вызовов**:

```
JOB_ERMITTELN, INFO, SG_IDENT_LESEN, SG_AIF_LESEN, SG_AIF_SCHREIBEN, SG_STATUS_LESEN,
SG_PROGRAMMIEREN, FEHLER_LOESCHEN, DATEN_REFERENZ, HW_REFERENZ, ZIF_BACKUP, U_PROG_LESEN,
GET_DIAG_PROT, SET_DIAG_PROT, SET_ECU_ADDRESS, SG_INNENTEMP_LESEN, SG_PHYS_HWNR_LESEN
```

Внутри `SG_PROGRAMMIEREN` (по строкам .ipo — реальный flash-flow):

1. `FLASH_PARAMETER_LESEN` → `SG_ADRESSE`, `FLASH_ZEITEN`, блок-параметры;
   `FLASH_PARAMETER_SETZEN` (адрес ЭБУ и параметры);
2. `FLASH_ZEITEN_LESEN` → `FLASH_LOESCHZEIT`, `FLASH_SIGNATURTESTZEIT`, `FLASH_RESETZEIT`,
   `FLASH_AUTHENTISIERZEIT`;
3. `FLASH_BLOCKLAENGE_LESEN` → `FLASH_BLOCKLAENGE_GESAMT`, `FLASH_BLOCKLAENGE_DATEN`;
4. `FLASH_PROGRAMMIER_STATUS_LESEN` → `FLASH_PROGRAMMIER_STATUS` (до программирования, после
   программирования, после подписи, после RESET; тексты: *«Programmierstatus nicht plausibel»*,
   *«SG meldet Programmierung NOK. Abbruch!!»*, *«Programmierung erfolgreich beendet»*);
5. `FLASH_LOESCHEN` (стирание; обработка `RoutineNotComplete`, *«Ueberschreitung der
   FlashLoeschzeit»*);
6. `AUTHENTISIERUNG_ZUFALLSZAHL_LESEN` (challenge) → `AUTHENTISIERUNG_START`
   (варианты **`Symetrisch`** и **`Asymetrisch`**!) → `AuthentisierungZeit`;
7. `FLASH_SCHREIBEN_ADRESSE`, затем `FLASH_SCHREIBEN` / `FLASH_SCHREIBEN_XXL` /
   `FLASH_SCHREIBEN_STATUS` / `FLASH_SCHREIBEN_ENDE` (`DatenDownload` / `DownloadEnde`);
8. `FLASH_SIGNATUR_PRUEFEN` (текст ошибки *«Fehler im Aufruf der Signaturpruefung»*);
9. `STEUERGERAETE_RESET` / `STEUERGERAETE_RESET_DELAY`;
10. `U_PROG_LESEN` (`U_PROG`), `FEHLER_LOESCHEN`, `AIF_LESEN`/`AIF_SCHREIBEN`, `ZIF_LESEN`/
    `ZIF_BACKUP_LESEN`.

Полный список job'ов KOMB87 (133 шт.) уже задокументирован локально в
`прошивки приборок/KOMB87_JOBS.md`: `FLASH_ZEITEN_LESEN`, `FLASH_BLOCKLAENGE_LESEN`,
`AUTHENTISIERUNG_ZUFALLSZAHL_LESEN`, `AUTHENTISIERUNG_START`, `FLASH_PROGRAMMIER_STATUS_LESEN`,
`FLASH_SIGNATUR_PRUEFEN`, `FLASH_LOESCHEN`, `FLASH_SCHREIBEN_ADRESSE`, `FLASH_SCHREIBEN`,
`FLASH_SCHREIBEN_ENDE`, `STEUERGERAETE_RESET`, `SPEICHER_LESEN`/`SPEICHER_SCHREIBEN`,
`DIAGNOSE_MODE`, `DIAGNOSE_AUFRECHT`, `DIAGNOSE_ENDE`, `DIAGNOSEPROTOKOLL_LESEN`/`_SETZEN`.

Вывод: **прошивка приборки — это не «erase + write» на голом KWP2000**. Это оркестрация из
~15 job'ов двух SGBD (приложенческого `KOMB87` и флеш-`FLASH`), с таблицей временных лимитов,
challenge-response аутентификацией (симметричной и асимметричной), проверкой статуса
программирования на 4 контрольных точках, AIF/UIF-полями и подписью. Всё это — логика SGBD,
которую нельзя «угадать» по байтам.

### 5.2. Пропускная способность и время (оценка, не измерение)

* 500 kbit/s, кадр CAN с 8 байтами данных + служебные поля и bit-stuffing ≈ 110–135 бит
  → ~3700–4500 кадров/с в одну сторону при идеальной загрузке.
* ISO-TP в операции записи: 6–7 байт полезных данных на consecutive frame, плюс first frame,
  flow-control и паузы `STmin`, плюс ответы ЭБУ (`FLASH_SCHREIBEN_STATUS`).
  Реалистично **5–25 КБ/с** эффективной записи.
* Для образа ~256–260 КБ → ориентировочно **от ~15 с (идеал) до 1–3 минут** только на передачу
  данных, плюс стирание флеша (десятки секунд), подпись и несколько RESET'ов. Итоговое время
  прошивки приборки — **единицы минут**.
* Точных измеренных цифр (KB/s, время прошивки KOMBI на E9x) в открытых источниках **не
  найдено** — это оценка на основе расчёта, помечена как неподтверждённая.

### 5.3. Условия по питанию

* Таблица вендора зарядных устройств (Clore Automotive, «OE-Specified Voltage Environment for
  Reprogramming»): **BMW — 14.2 В**, для литиевых АКБ **13.8 В**
  ([PDF](https://cloreautomotive.com/wp-content/uploads/2025/03/OE-Specified-Voltage-Reprogramming-2025.pdf)).
* Практика BMW/ISTA/WinKFP (широко распространённое требование, первичным документом здесь **не
  подтверждено**): зажигание включено, двигатель выключен, внешний источник питания/зарядное
  устройство подключено, напряжение держится **не ниже ~13.0–13.5 В** на протяжении всей
  процедуры, запрещено прерывание связи/питания.
* Риск: прерывание прошивки приборки → «кирпич» (у платформы нет штатного recovery через OBD,
  кроме повторного захода бутлоадером, который сам может быть недоступен). Это главный аргумент
  против самодельного flash-стека.

---

## 6. Рекомендуемая архитектура

Разделить «чтение/актуация» и «прошивку» — у них разная цена ошибки.

**Слой 1 — транспорт (пишем сами, Python, ~400 строк):**

```
serial(115200, 8N1)                       # pyserial
  └── BmwFastCodec: build/parse телеграммы [0x80|len][TGT][SRC][data][sum8]
  └── AdapterProbe: опрос кабеля (82 F1 F1 FE/FD/FB/FC)
  └── Kwp2000Session: W1..W5, P1..P4, NR78(0x78), echo, TesterPresent-таймер
  └── (опционально) IsoTpSession для adapter-telegram CAN (00 03 02 ... 6F1 ...)
```

**Слой 2 — задания:** таблица «job → байты запроса», извлечённая офлайн из SP-Daten
(`tools/sgbd_extract.py` из соседнего проекта уже это умеет) + разбор ответов. Покрывает
`IDENT`, `STATUS_*`, `STEUERN_*`, `FS_LESEN/FS_LOESCHEN`, `SPEICHER_LESEN`.

**Слой 3 — прошивка:** реализовать полностью самим **не рекомендуется**. Варианты:
`.NET`-sidecar (EdiabasLib/`EdiabasNet`) или Windows-хост с EDIABAS/`api32.dll`; Python-часть
общается с ним по JSON-RPC (ровно этот паттерн уже реализован в ediabasx:
`ediabasx serve` + `EdiabasClient`). Это даёт настоящий BEST/2-интерпретатор, а значит все
`FLASH_*`, `AUTHENTISIERUNG_*`, `AIF_*`, `U_PROG_LESEN` работают «как у BMW» без реверса.

### 6.1. Сравнение трёх вариантов

| Критерий | (a) Свой D-CAN+KWP2000 на pyserial | (b) EdiabasLib/EdiabasNet как транспорт | (c) Обёртка над EDIABAS/Tool32 |
|---|---|---|---|
| Язык/платформа | Python, кроссплатформенно | .NET (pythonnet / sidecar) | Windows, 32-bit Python |
| Лицензия | своя | **GPL-3.0 → заражает закрытый продукт** | EDIABAS — проприетарный BMW, распространяется неофициально |
| Транспорт D-CAN | достаточно, если кабель «умный» | есть (EDIC/custom/ENET/ELM) | есть (через OBD32/EDIABAS) |
| Прошивка KOMBI | **почти нереально** без реверса SGBD | реально: BEST/2-интерпретатор исполняет `FLASH_*` | реально: WinKFP/Tool32 «как задумано BMW» |
| Риск «кирпича» | высокий | средний | минимальный |
| Объём работ | 400 строк до чтения; месяцы до прошивки | дни на интеграцию | дни на интеграцию, но Windows-only |
| Отладка | полный контроль (можно логировать каждый байт) | трассы IFH есть | трассы EDIABAS есть |

**Вердикт:**
1. **Сейчас — (a)** для чтения и актуации: это быстро, безопасно и уже проверено на живых
   данных (соседний проект читает DME запросом `30 0A 01`). Слой транспорта из (a) нужен в любом
   случае — он же будет логгером/сниффером и «вторым мнением» при отладке.
2. **Для прошивки — (b) или (c)**, спрятанные за интерфейсом `FlashEngine`. Если продукт
   открытый/внутренний — (b) (кроссплатформенно, современно, есть готовый JSON-RPC-паттерн).
   Если продукт закрытый и Windows допустим — (c) через `pydiabas`/`api32.dll` (лицензионные
   риски EDIABAS при этом остаются на стороне пользователя).
3. **(a)-only для прошивки** выбирать только при готовности к долгому реверсу
   (`FLASH_PARAMETER_*`, аутентификация, подпись) и с аппаратным программатором как recovery.

---

## 7. Что подтверждено, а что нет

**Подтверждено кодом/документами:** формат BMW-FAST и сумма; ID `0x6F1`, формула ответа
`0x600|адрес ЭБУ`, extended addressing; концепт `0x0110` = D-CAN с UART 115200 8N1; наличие
командного протокола у «умного» кабеля (опрос `82 F1 F1 ..`) и байтовые форматы adapter-telegram
(telType 0x00/0x01/0x02/0x03); tester-present как параметр SGBD; тайминги P1–P4/W1–W5 и NR78;
чипсеты USB-UART в кабелях и требование latency 1 мс; полный список flash-job'ов и порядок
вызова из `10flash.prg` + `080100HKOML2.ipo`; подписи API `apiJob/apiJobData/apiInitExt/apiSetConfig`;
требование 32-битного Python для `pydiabas`.

**Не подтверждено / открыто:** конкретная модель MCU внутри K+DCAN-кабеля; наличие и значения
функционального CAN-ID (`0x6F0`/`0x7DF`) для BMW D-CAN; диагностический адрес `A` для KOMB87
(берётся из таблицы адресов SGBD `ECU_ADR_*` или задаётся приложением через `SetEcuAdr` — надо
прочитать из вашего SP-Daten); измеренная пропускная способность/время прошивки; точная схема
маршрутизации диагностических кадров шлюзом между D-CAN и K-CAN; командный batch-режим Tool32.

---

## 8. Ссылки

* EdiabasLib — <https://github.com/uholeschak/ediabaslib> (C#, GPL-3.0)
  * [EdInterfaceObd.cs](https://github.com/uholeschak/ediabaslib/blob/master/EdiabasLib/EdiabasLib/EdInterfaceObd.cs) ·
    [EdInterfaceEdic.cs](https://github.com/uholeschak/ediabaslib/blob/master/EdiabasLib/EdiabasLib/EdInterfaceEdic.cs) ·
    [EdCustomAdapterCommon.cs](https://github.com/uholeschak/ediabaslib/blob/master/EdiabasLib/EdiabasLib/EdCustomAdapterCommon.cs) ·
    [EdElmInterface.cs](https://github.com/uholeschak/ediabaslib/blob/master/EdiabasLib/EdiabasLib/EdElmInterface.cs) ·
    [EdInterfaceBase.cs](https://github.com/uholeschak/ediabaslib/blob/master/EdiabasLib/EdiabasLib/EdInterfaceBase.cs)
  * [docs/AdapterTypes.md](https://github.com/uholeschak/ediabaslib/blob/master/docs/AdapterTypes.md) ·
    [docs/EdiabasLib.config_file.md](https://github.com/uholeschak/ediabaslib/blob/master/docs/EdiabasLib.config_file.md)
  * тестовый D-CAN SGBD: `EdiabasLib/Test/Ecu/d60m47a0_dcan.prg` (в репозитории)
* ediabasx — <https://github.com/emdzej/ediabasx> (TypeScript, лицензия NOASSERTION)
  * [SerialInterface.ts](https://github.com/emdzej/ediabasx/blob/main/packages/interface-serial/src/SerialInterface.ts) ·
    [kdcan/telegram.ts](https://github.com/emdzej/ediabasx/blob/main/packages/interface-serial/src/kdcan/telegram.ts) ·
    [kdcan/adapterInfo.ts](https://github.com/emdzej/ediabasx/blob/main/packages/interface-serial/src/kdcan/adapterInfo.ts) ·
    [kdcan/adapterTransport.ts](https://github.com/emdzej/ediabasx/blob/main/packages/interface-serial/src/kdcan/adapterTransport.ts) ·
    [kdcan/kwp2000.ts](https://github.com/emdzej/ediabasx/blob/main/packages/interface-serial/src/kdcan/kwp2000.ts) ·
    [kdcan/dcan.ts](https://github.com/emdzej/ediabasx/blob/main/packages/interface-serial/src/kdcan/dcan.ts) ·
    [kdcan/constants.ts](https://github.com/emdzej/ediabasx/blob/main/packages/interface-serial/src/kdcan/constants.ts) ·
    [ediabas/config-schema.ts](https://github.com/emdzej/ediabasx/blob/main/packages/ediabas/src/config-schema.ts)
  * `docs/interfaces/obd32-protocols.md`, `reference/*.c` (декомпилированные `api32.dll`, `OBD32.dll`, `ebas32.dll`)
* pydiabas — <https://github.com/BembelBytes/pydiabas> · PyPI <https://pypi.org/project/pydiabas/> (Python, MIT)
* garagediag — <https://github.com/tooming/garagediag> (Python; `ds2_diag.py`, `kline_obd.py`, `isotp.py`)
* QFLASH21 — <https://github.com/batko15/QFLASH21> (TS/Web Serial, KWP2000 flash, таблица чипсетов)
* node-bmw-client — <https://github.com/kmalinich/node-bmw-client> (JS, MIT)
* open-can-controller — <https://github.com/ilicmiljan/open-can-controller> (CAN-контроллер для приборок E9X)
* python-can-isotp — <https://github.com/pylessard/python-can-isotp> (MIT) · python-udsoncan — <https://github.com/pylessard/python-udsoncan> (MIT) · python-can — <https://pypi.org/project/python-can/> · pyserial — <https://github.com/pyserial/pyserial>
* OpenJ2534 — <https://github.com/jakka351/OpenJ2534>
* EDIABAS API Function Primer (зеркало) — <http://obdrus.ru/f/apiref.pdf>
* BEST/2 user guide (зеркало) — <http://obdrus.ru/d/787731/d/bestuser.pdf>
* BMW Standard Tools / Tool32 docs — <https://git.0x45.cz/em/bmw-advanced-tools>
* Вендор K+DCAN — [APN_Connection_Stability.pdf](https://www.one-stop-electronics.com/wp-content/uploads/2023/05/APN_Connection_Stability.pdf)
* Teardown/предупреждение о кабелях — <http://www.auto-diagnosis.org/warning-for-bad-kdcan-cable/>
* Переключатель pin 7/8 — <http://blog.uobdii.com/kdcan-cable-with-switch-pin-78-good-or-not/>
* FT232 EEPROM настройки кабелей — <https://www.e46fanatics.com/threads/ft232-eeprom-settings-k-d-can-cables.1097604/>
* Требования по напряжению при перепрограммировании — [Clore Automotive](https://cloreautomotive.com/wp-content/uploads/2025/03/OE-Specified-Voltage-Reprogramming-2025.pdf)
* Локальные артефакты проекта: `прошивки приборок/10flash.prg`, `прошивки приборок/080100HKOML2.ipo`,
  `прошивки приборок/KOMB87_JOBS.md`, `bmw-e90-can-display/docs/diag-jobs.md`,
  `BimmerDaten/decoderPrg.py`
