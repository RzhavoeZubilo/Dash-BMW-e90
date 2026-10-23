// Сгенерировано: python3 tools/site/build_jobs_data.py
// Источник: docs/research/KOMB87_JOBS.md -- не редактировать руками.
window.KOMBI_JOBS = [
  {
    "name": "INFO",
    "addr": "0x000000A0",
    "comment": "Information SGBD",
    "ru": "служебная информация о самом SGBD (версия, описание) — не про щиток, а про файл диагностики",
    "en": "service information about the SGBD itself (version, description) — about the diagnostic file, not the cluster",
    "tags": []
  },
  {
    "name": "INITIALISIERUNG",
    "addr": "0x000001FF",
    "comment": "Initialisierung und Kommunikationsparameter",
    "ru": "открывает диагностическую сессию и задаёт параметры связи (скорость, протокол) перед остальными джобами",
    "en": "opens a diagnostic session and sets communication parameters (speed, protocol) before any other job",
    "tags": []
  },
  {
    "name": "DIAGNOSEPROTOKOLL_LESEN",
    "addr": "0x0000276E",
    "comment": "Gibt die möglichen Diagnoseprotokolle",
    "ru": "узнать, какие диагностические протоколы (KWP2000 и т.п.) поддерживает щиток",
    "en": "find out which diagnostic protocols (KWP2000 etc.) the cluster supports",
    "tags": []
  },
  {
    "name": "DIAGNOSEPROTOKOLL_SETZEN",
    "addr": "0x00002C24",
    "comment": "Wählt ein Diagnoseprotokoll aus",
    "ru": "выбрать диагностический протокол для текущей сессии",
    "en": "select the diagnostic protocol for the current session",
    "tags": []
  },
  {
    "name": "IDENT",
    "addr": "0x00002E8B",
    "comment": "Identdaten",
    "ru": "прочитать идентификационные данные щитка (номер детали, версия ПО и т.п.) — то же самое, что видно в INPA/ISTA в разделе \"идентификация\"",
    "en": "read the cluster identification (part number, software version etc.) — the same data INPA/ISTA show under \"identification\"",
    "tags": []
  },
  {
    "name": "FS_LESEN",
    "addr": "0x00005443",
    "comment": "Fehlerspeicher lesen (alle Fehler / Ort und Art)",
    "ru": "прочитать журнал ошибок целиком: все коды неисправностей со статусом (место и тип ошибки)",
    "en": "read the whole fault memory: every fault code with its status (location and type)",
    "tags": []
  },
  {
    "name": "FS_LESEN_DETAIL",
    "addr": "0x000074E2",
    "comment": "Fehlerspeicher lesen (ein Fehler / alle Details)",
    "ru": "прочитать подробности одной конкретной ошибки из журнала (все поля по одному коду)",
    "en": "read the details of one specific fault (all fields for a single code)",
    "tags": []
  },
  {
    "name": "FS_LOESCHEN",
    "addr": "0x000119B7",
    "comment": "Fehlerspeicher loeschen",
    "ru": "очистить журнал ошибок (аналог кнопки \"удалить ошибки\" в диагностике)",
    "en": "clear the fault memory (the \"clear faults\" button in diagnostics)",
    "tags": []
  },
  {
    "name": "PRUEFSTEMPEL_LESEN",
    "addr": "0x000126B4",
    "comment": "Auslesen des Pruefstempels",
    "ru": "прочитать \"штамп проверки\" — отметку о прохождении заводского/сервисного теста",
    "en": "read the \"test stamp\" — the mark that a factory/service test was passed",
    "tags": []
  },
  {
    "name": "PRUEFSTEMPEL_SCHREIBEN",
    "addr": "0x00013417",
    "comment": "Beschreiben des Pruefstempels",
    "ru": "записать \"штамп проверки\" (используется на заводе/в сервисе после теста)",
    "en": "write the \"test stamp\" (used at the factory/workshop after a test)",
    "tags": []
  },
  {
    "name": "NORMALER_DATENVERKEHR",
    "addr": "0x0001452E",
    "comment": "Sperren bzw. Freigeben des normalen Datenverkehrs",
    "ru": "включить или выключить обычный обмен по шине (например, временно \"заглушить\" щиток на время диагностики)",
    "en": "enable or disable normal bus traffic (e.g. silence the cluster during diagnostics)",
    "tags": []
  },
  {
    "name": "DIAGNOSE_AUFRECHT",
    "addr": "0x0001638A",
    "comment": "Diagnosemode des SG aufrecht erhalten",
    "ru": "keep-alive: держать диагностическую сессию открытой (щиток сам выходит из режима диагностики, если его не \"пинговать\")",
    "en": "keep-alive: keeps the diagnostic session open (the cluster drops out of diagnostics if not pinged)",
    "tags": []
  },
  {
    "name": "DIAGNOSE_ENDE",
    "addr": "0x00017F80",
    "comment": "Diagnosemode des SG beenden",
    "ru": "штатно завершить диагностическую сессию",
    "en": "end the diagnostic session cleanly",
    "tags": []
  },
  {
    "name": "DIAGNOSE_MODE",
    "addr": "0x000187DB",
    "comment": "SG in bestimmten Diagnosemode bringen",
    "ru": "перевести щиток в определённый диагностический режим (расширенный доступ и т.п.)",
    "en": "switch the cluster into a specific diagnostic mode (extended access etc.)",
    "tags": []
  },
  {
    "name": "SLEEP_MODE",
    "addr": "0x000195DA",
    "comment": "SG in Sleep-Mode versetzen",
    "ru": "перевести щиток в спящий режим (энергосбережение)",
    "en": "put the cluster to sleep (power saving)",
    "tags": []
  },
  {
    "name": "ENERGIESPARMODE",
    "addr": "0x0001A31F",
    "comment": "Einstellen des Energiesparmodes",
    "ru": "настроить режим энергосбережения щитка",
    "en": "configure the cluster's energy-saving mode",
    "tags": []
  },
  {
    "name": "SPEICHER_LESEN",
    "addr": "0x0001B274",
    "comment": "Auslesen des Steuergeraete-Speichers",
    "ru": "универсальное чтение памяти щитка по сегменту+адресу (ROM/RAM/flash/EEPROM напрямую, в обход коддинга) — именно этот джоб использует `tools/fujitsu_uart_flasher/`-подобный доступ по диагностике",
    "en": "generic memory read by segment + address (ROM/RAM/flash/EEPROM directly, bypassing coding) — the diagnostic-path counterpart of the UART dump",
    "tags": []
  },
  {
    "name": "SPEICHER_SCHREIBEN",
    "addr": "0x0001C6D6",
    "comment": "Beschreiben des Steuergeraete-Speichers",
    "ru": "универсальная запись в память щитка по сегменту+адресу, низкоуровневый аналог `SPEICHER_LESEN`",
    "en": "generic memory write by segment + address, the low-level counterpart of `SPEICHER_LESEN`",
    "tags": []
  },
  {
    "name": "CBS_INFO",
    "addr": "0x0001E282",
    "comment": "Ausgabe der CBS-Version",
    "ru": "версия подсистемы CBS (Condition Based Service — сервисные интервалы \"по состоянию\")",
    "en": "version of the CBS subsystem (Condition Based Service — condition-based service intervals)",
    "tags": []
  },
  {
    "name": "CBS_DATEN_LESEN",
    "addr": "0x0001E6C2",
    "comment": "CBS Daten auslesen (fuer CBS-Version 4)",
    "ru": "прочитать данные CBS (остаток до следующих ТО, замены масла и т.д.), версия формата 4",
    "en": "read CBS data (what is left until the next service, oil change etc.), format version 4",
    "tags": []
  },
  {
    "name": "CBS_RESET",
    "addr": "0x0002584B",
    "comment": "CBS Daten Zuruecksetzen (fuer CBS-Version 4)",
    "ru": "сбросить данные CBS (имитация выполненного сервисного обслуживания)",
    "en": "reset CBS data (as if a service was performed)",
    "tags": []
  },
  {
    "name": "PRUEFCODE_LESEN",
    "addr": "0x0002757E",
    "comment": "Standard Pruefcode lesen fuer Kundendienst",
    "ru": "прочитать стандартный проверочный код для сервисного приёмщика (контроль подлинности/состояния)",
    "en": "read the standard check code for the service advisor (authenticity/state check)",
    "tags": []
  },
  {
    "name": "C_CI_LESEN",
    "addr": "0x0002906C",
    "comment": "Codierindex lesen",
    "ru": "прочитать индекс кодирования (версию набора параметров FSW/PSW, по которому щиток закодирован)",
    "en": "read the coding index (the FSW/PSW parameter set version the cluster is coded with)",
    "tags": [
      "CODING"
    ]
  },
  {
    "name": "C_FG_LESEN",
    "addr": "0x0002AF48",
    "comment": "Fahrgestellnummer lesen",
    "ru": "прочитать записанный в щитке VIN (номер кузова)",
    "en": "read the VIN stored in the cluster",
    "tags": [
      "CODING"
    ]
  },
  {
    "name": "C_FG_SCHREIBEN",
    "addr": "0x0002C0B1",
    "comment": "Fahrgestellnummer schreiben",
    "ru": "записать VIN в щиток (привязка к конкретному автомобилю)",
    "en": "write the VIN into the cluster (binds it to a specific car)",
    "tags": [
      "CODING"
    ]
  },
  {
    "name": "C_FG_AUFTRAG",
    "addr": "0x0002D320",
    "comment": "Fahrgestellnummer schreiben und ruecklesen",
    "ru": "записать VIN и сразу прочитать обратно для проверки записи",
    "en": "write the VIN and read it back to verify",
    "tags": [
      "CODING"
    ]
  },
  {
    "name": "C_AEI_LESEN",
    "addr": "0x0002F32C",
    "comment": "Aenderungsindex der Codierdaten lesen",
    "ru": "прочитать индекс изменения коддинг-данных (счётчик версий коддинга)",
    "en": "read the coding change index (coding version counter)",
    "tags": [
      "CODING"
    ]
  },
  {
    "name": "C_AEI_SCHREIBEN",
    "addr": "0x000305BE",
    "comment": "Aenderungsindex der Codierdaten schreiben",
    "ru": "записать индекс изменения коддинг-данных",
    "en": "write the coding change index",
    "tags": [
      "CODING"
    ]
  },
  {
    "name": "C_AEI_AUFTRAG",
    "addr": "0x0003195B",
    "comment": "Aenderungsindex der Codierdaten schreiben und ruecklesen",
    "ru": "записать индекс изменения коддинг-данных и сразу перечитать для проверки",
    "en": "write the coding change index and read it back to verify",
    "tags": [
      "CODING"
    ]
  },
  {
    "name": "C_C_LESEN",
    "addr": "0x00033A48",
    "comment": "Codierdaten lesen",
    "ru": "прочитать блок коддинг-данных (параметры комплектации FSW/PSW)",
    "en": "read a coding data block (equipment parameters FSW/PSW)",
    "tags": [
      "CODING"
    ]
  },
  {
    "name": "C_C_SCHREIBEN",
    "addr": "0x00034ECF",
    "comment": "Codierdaten schreiben",
    "ru": "**главный джоб кодирования** — именно его использует NCS Expert/ISTA для записи коддинга (FSW/PSW) через `$22`/`$2E`, диапазон `$3000-$3EFF`",
    "en": "**the main coding job** — what NCS Expert/ISTA use to write coding (FSW/PSW) via `$22`/`$2E`, range `$3000-$3EFF`",
    "tags": [
      "CODING"
    ]
  },
  {
    "name": "C_C_AUFTRAG",
    "addr": "0x00036384",
    "comment": "Codierdaten schreiben und ruecklesen",
    "ru": "записать блок коддинг-данных и сразу перечитать для проверки",
    "en": "write a coding data block and read it back to verify",
    "tags": [
      "CODING"
    ]
  },
  {
    "name": "SERIENNUMMER_LESEN",
    "addr": "0x000386FD",
    "comment": "Hersteller Seriennummer lesen",
    "ru": "прочитать серийный номер производителя (не VIN, а номер самого блока щитка)",
    "en": "read the manufacturer serial number (of the cluster unit itself, not the VIN)",
    "tags": []
  },
  {
    "name": "ZIF_LESEN",
    "addr": "0x00039B9A",
    "comment": "Auslesen des Zulieferinfofeldes",
    "ru": "прочитать \"информационное поле поставщика\" (служебные данные производителя щитка, Siemens VDO/Johnson Controls)",
    "en": "read the \"supplier information field\" (manufacturer service data, Siemens VDO/Johnson Controls)",
    "tags": []
  },
  {
    "name": "ZIF_BACKUP_LESEN",
    "addr": "0x0003C7F7",
    "comment": "Auslesen des Backups des Zulieferinfofeldes",
    "ru": "прочитать резервную копию ZIF-поля (на случай повреждения основного)",
    "en": "read the backup copy of the ZIF field (in case the main one is damaged)",
    "tags": []
  },
  {
    "name": "PHYSIKALISCHE_HW_NR_LESEN",
    "addr": "0x0003E3D0",
    "comment": "Auslesen der physikalischen Hardwarenummer",
    "ru": "прочитать физический номер железа (HW-NR) — именно его проверяет WinKFP перед прошивкой, см. раздел про привязку софта к железу в исследовании",
    "en": "read the physical hardware number (HW-NR) — what WinKFP checks before flashing, see the software-to-hardware binding section in the research",
    "tags": []
  },
  {
    "name": "HARDWARE_REFERENZ_LESEN",
    "addr": "0x0003F985",
    "comment": "Auslesen der Hardware Referenz",
    "ru": "прочитать референс аппаратной платформы щитка",
    "en": "read the hardware platform reference of the cluster",
    "tags": []
  },
  {
    "name": "DATEN_REFERENZ_LESEN",
    "addr": "0x00040FF1",
    "comment": "Auslesen der Daten Referenz",
    "ru": "прочитать референс набора данных (версию прошитых данных/таблиц)",
    "en": "read the data set reference (version of the flashed data/tables)",
    "tags": []
  },
  {
    "name": "FLASH_ZEITEN_LESEN",
    "addr": "0x00041F71",
    "comment": "Auslesen der Flash Loeschzeit, Signaturtestzeit,",
    "ru": "прочитать тайминги прошивки: сколько займёт стирание флеша и проверка подписи (нужно клиенту диагностики, чтобы не обрывать сессию раньше времени)",
    "en": "read flashing timings: how long erasing and signature checking take (so the tester does not drop the session too early)",
    "tags": []
  },
  {
    "name": "FLASH_BLOCKLAENGE_LESEN",
    "addr": "0x00042E2E",
    "comment": "Auslesen des maximalen Blocklaenge beim Flashen",
    "ru": "прочитать максимальный размер блока данных за одну передачу при прошивке",
    "en": "read the maximum data block size per transfer when flashing",
    "tags": []
  },
  {
    "name": "AUTHENTISIERUNG_ZUFALLSZAHL_LESEN",
    "addr": "0x0004390A",
    "comment": "Authentisierung Zufallszahl des SG lesen",
    "ru": "первый шаг challenge-response авторизации перед прошивкой: получить от щитка случайное число (challenge)",
    "en": "first step of the challenge-response authentication before flashing: get a random number (challenge) from the cluster",
    "tags": [
      "FIRMWARE"
    ]
  },
  {
    "name": "AUTHENTISIERUNG_START",
    "addr": "0x000446AD",
    "comment": "Authentisierung pruefen",
    "ru": "второй шаг: отправить ответ (подписанное случайное число) и получить допуск к прошивке",
    "en": "second step: send the answer (signed random number) and get permission to flash",
    "tags": [
      "FIRMWARE"
    ]
  },
  {
    "name": "FLASH_PROGRAMMIER_STATUS_LESEN",
    "addr": "0x00046502",
    "comment": "Programmierstatus des SG lesen",
    "ru": "узнать текущий статус процесса прошивки (идёт/завершена/ошибка)",
    "en": "current state of the flashing process (running/finished/error)",
    "tags": [
      "FIRMWARE"
    ]
  },
  {
    "name": "FLASH_SIGNATUR_PRUEFEN",
    "addr": "0x0004705E",
    "comment": "Flash Signatur pruefen",
    "ru": "проверить криптографическую подпись прошивки (последний шаг после записи, без успешной проверки новая прошивка не применится)",
    "en": "verify the cryptographic signature of the firmware (final step after writing; without it the new firmware is not accepted)",
    "tags": [
      "FIRMWARE"
    ]
  },
  {
    "name": "STEUERGERAETE_RESET",
    "addr": "0x00048B74",
    "comment": "Steuergeraete reset ausloesen",
    "ru": "перезагрузить блок (программный ресет щитка)",
    "en": "reboot the module (software reset of the cluster)",
    "tags": []
  },
  {
    "name": "FLASH_LOESCHEN",
    "addr": "0x000493D0",
    "comment": "Flash loeschen",
    "ru": "стереть область флеша перед записью новой прошивки",
    "en": "erase a flash area before writing new firmware",
    "tags": [
      "FIRMWARE"
    ]
  },
  {
    "name": "FLASH_SCHREIBEN_ADRESSE",
    "addr": "0x0004B1EB",
    "comment": "Vorbereitung fuer Flash schreiben",
    "ru": "подготовка к прошивке: сообщить щитку адрес и размер блока, который сейчас будет передаваться",
    "en": "flashing preparation: tell the cluster the address and size of the block about to be sent",
    "tags": [
      "FIRMWARE"
    ]
  },
  {
    "name": "FLASH_SCHREIBEN",
    "addr": "0x0004C0B2",
    "comment": "Flash Daten schreiben",
    "ru": "передать и записать очередной блок данных прошивки во флеш",
    "en": "transfer and write the next firmware data block to flash",
    "tags": [
      "FIRMWARE"
    ]
  },
  {
    "name": "FLASH_SCHREIBEN_ENDE",
    "addr": "0x0004D01F",
    "comment": "Flashprogrammierung abschliessen",
    "ru": "завершить процесс прошивки (финальный шаг после передачи всех блоков)",
    "en": "finish the flashing process (final step after all blocks are sent)",
    "tags": [
      "FIRMWARE"
    ]
  },
  {
    "name": "AIF_LESEN",
    "addr": "0x0004DD1C",
    "comment": "Auslesen des Anwender Informations Feldes",
    "ru": "прочитать \"информационное поле пользователя\" (служебная область для заметок/меток, не влияет на работу щитка)",
    "en": "read the \"user information field\" (a service area for notes/labels, does not affect operation)",
    "tags": []
  },
  {
    "name": "AIF_SCHREIBEN",
    "addr": "0x00050874",
    "comment": "Schreiben des Anwender Informations Feldes",
    "ru": "записать \"информационное поле пользователя\"",
    "en": "write the \"user information field\"",
    "tags": []
  },
  {
    "name": "SG_RESET_OHNE_UHR_DATUM",
    "addr": "0x00054EF7",
    "comment": "Steuergeraete Reset ausloesen",
    "ru": "перезагрузить блок, не сбрасывая часы и дату (в отличие от обычного ресета)",
    "en": "reboot the module without resetting the clock and date (unlike a normal reset)",
    "tags": []
  },
  {
    "name": "UHRZEIT_DATUM_STELLEN",
    "addr": "0x000552A0",
    "comment": "Uhrzeit und Datum stellen",
    "ru": "установить время и дату в щитке",
    "en": "set the time and date in the cluster",
    "tags": []
  },
  {
    "name": "CODIERDATEN_LESEN",
    "addr": "0x00055FFA",
    "comment": "(чтение блока 0x3000-0x3FFF по номеру блока)",
    "ru": "прочитать блок коддинга напрямую по номеру блока (диапазон `0x3000-0x3FFF`), более низкоуровневый вариант чтения, чем `C_C_LESEN`",
    "en": "read a coding block directly by block number (range `0x3000-0x3FFF`), lower level than `C_C_LESEN`",
    "tags": [
      "CODING"
    ]
  },
  {
    "name": "C_CHECKSUMME",
    "addr": "0x0005665A",
    "comment": "Checksumme generieren und in BINAER_BUFFER schreiben",
    "ru": "посчитать контрольную сумму блока коддинга перед записью (не крипто-подпись, просто checksum для защиты от битых данных)",
    "en": "compute the checksum of a coding block before writing (not a crypto signature, just a checksum against corrupted data)",
    "tags": [
      "CODING"
    ]
  },
  {
    "name": "STEUERN_LEUCHTEN",
    "addr": "0x00056DAA",
    "comment": "Kontrolleuchten im Kombi ansteuern",
    "ru": "принудительно включить контрольные лампы на щитке (для проверки лампочек сервисменом)",
    "en": "force the warning lamps on (lamp check by a technician)",
    "tags": []
  },
  {
    "name": "STEUERN_LEUCHTEN_BLAU",
    "addr": "0x000581A0",
    "comment": "Blaue Leuchten im Kombi ansteuern",
    "ru": "включить только синие контрольные лампы (тест по цвету)",
    "en": "turn on only the blue lamps (colour test)",
    "tags": []
  },
  {
    "name": "STEUERN_LEUCHTEN_GELB",
    "addr": "0x0005854E",
    "comment": "Gelbe Leuchten im Kombi ansteuern",
    "ru": "включить только жёлтые контрольные лампы (тест по цвету)",
    "en": "turn on only the yellow lamps (colour test)",
    "tags": []
  },
  {
    "name": "STEUERN_LEUCHTEN_GRUEN",
    "addr": "0x000588FC",
    "comment": "Gruene Leuchten im Kombi ansteuern",
    "ru": "включить только зелёные контрольные лампы (тест по цвету)",
    "en": "turn on only the green lamps (colour test)",
    "tags": []
  },
  {
    "name": "STEUERN_LEUCHTEN_ORANGE",
    "addr": "0x0005902C",
    "comment": "Gelbe Leuchten im Kombi ansteuern",
    "ru": "включить только оранжевые/жёлтые контрольные лампы (тест по цвету)",
    "en": "turn on only the orange/amber lamps (colour test)",
    "tags": []
  },
  {
    "name": "STEUERN_LEUCHTEN_ROT",
    "addr": "0x000593DA",
    "comment": "Rote Leuchten im Kombi ansteuern",
    "ru": "включить только красные контрольные лампы (тест по цвету)",
    "en": "turn on only the red lamps (colour test)",
    "tags": []
  },
  {
    "name": "STEUERN_LEUCHTEN_AUS",
    "addr": "0x00059788",
    "comment": "Wenn vorher der Job STEUERN_LEUCHTEN aufgerufen wurde",
    "ru": "выключить принудительное управление лампами, запущенное `STEUERN_LEUCHTEN`, вернуть обычный режим",
    "en": "stop the forced lamp control started by `STEUERN_LEUCHTEN`, back to normal",
    "tags": []
  },
  {
    "name": "STEUERN_BLINKER",
    "addr": "0x00059EB2",
    "comment": "Blinker ansteuern, fuer Service-und Testzwecke",
    "ru": "принудительно включить указатели поворота (сервисный тест)",
    "en": "force the turn indicators on (service test)",
    "tags": []
  },
  {
    "name": "STEUERN_BLINKER_AUS",
    "addr": "0x0005A673",
    "comment": "Wenn vorher der Job STEUERN_BLINKER aufgerufen wurde",
    "ru": "выключить принудительное управление поворотниками, запущенное `STEUERN_BLINKER`",
    "en": "stop the forced indicator control started by `STEUERN_BLINKER`",
    "tags": []
  },
  {
    "name": "STEUERN_SELBSTTEST_EIN",
    "addr": "0x0005AA1D",
    "comment": "Schaltet den Selbttest ein",
    "ru": "включить режим самотестирования щитка (проверка стрелок/экрана/ламп при включении)",
    "en": "start the cluster self-test (needles/display/lamps check as at power-up)",
    "tags": []
  },
  {
    "name": "STEUERN_SELBSTTEST_AUS",
    "addr": "0x0005B02E",
    "comment": "Schaltet den Selbsttest wieder aus",
    "ru": "выключить режим самотестирования",
    "en": "stop the self-test",
    "tags": []
  },
  {
    "name": "STEUERN_TACHO",
    "addr": "0x0005B3D8",
    "comment": "Tacho auf beliebige Geschwindigkeit (0..300) setzen  (временно, сессия)",
    "ru": "задать произвольное показание спидометра (0..300 км/ч) — временно, только на время сессии, для проверки стрелки/экрана",
    "en": "set an arbitrary speedometer reading (0..300 km/h) — temporary, only for the session, to check the needle/display",
    "tags": []
  },
  {
    "name": "STEUERN_TACHO_AUS",
    "addr": "0x0005C1BF",
    "comment": "Schaltet den Tacho-Vorgabemodus wieder aus",
    "ru": "выключить принудительное задание скорости, вернуть реальные показания",
    "en": "stop forcing the speed, back to real readings",
    "tags": []
  },
  {
    "name": "STEUERN_DREHZAHL",
    "addr": "0x0005C569",
    "comment": "DrehZahlMesser in 1/min vorgeben  (временно, сессия)",
    "ru": "задать произвольные обороты тахометра (об/мин) — временно, на время сессии",
    "en": "set an arbitrary tachometer reading (rpm) — temporary, for the session",
    "tags": []
  },
  {
    "name": "STEUERN_DREHZAHL_AUS",
    "addr": "0x0005D3C3",
    "comment": "Schaltet den DZM-Vorgabemodus wieder aus",
    "ru": "выключить принудительное задание оборотов, вернуть реальные показания",
    "en": "stop forcing the rpm, back to real readings",
    "tags": []
  },
  {
    "name": "STEUERN_KVA",
    "addr": "0x0005D76D",
    "comment": "Momentanverbrauch in L/100km vorgeben  (временно, сессия)",
    "ru": "задать произвольный мгновенный расход топлива (л/100км) — временно, на время сессии",
    "en": "set an arbitrary instant fuel consumption (l/100 km) — temporary, for the session",
    "tags": []
  },
  {
    "name": "STEUERN_KVA_AUS",
    "addr": "0x0005E8E4",
    "comment": "Schaltet den KVA-Vorgabemodus wieder aus",
    "ru": "выключить принудительное задание расхода, вернуть реальные показания",
    "en": "stop forcing consumption, back to real readings",
    "tags": []
  },
  {
    "name": "STEUERN_TANK",
    "addr": "0x0005EC8E",
    "comment": "Tankinhalt in % vorgeben",
    "ru": "задать произвольный уровень топлива в баке (%) — для проверки стрелки/индикатора",
    "en": "set an arbitrary fuel level (%) — to check the needle/indicator",
    "tags": []
  },
  {
    "name": "STEUERN_TANK_AUS",
    "addr": "0x0005F951",
    "comment": "Schaltet den Tank-Vorgabemodus wieder aus",
    "ru": "выключить принудительное задание уровня топлива, вернуть реальные показания",
    "en": "stop forcing the fuel level, back to real readings",
    "tags": []
  },
  {
    "name": "STEUERN_ACC_ZEIGER",
    "addr": "0x0005FCFB",
    "comment": "Geschwindigkeit fuer ACC-Zeiger in km/h vorgeben  (временно, сессия)",
    "ru": "задать произвольную скорость для стрелки/индикатора ACC (круиз-контроль) — временно, на время сессии",
    "en": "set an arbitrary speed for the ACC (cruise control) needle/indicator — temporary, for the session",
    "tags": []
  },
  {
    "name": "STEUERN_ACC_ZEIGER_AUS",
    "addr": "0x00060D5B",
    "comment": "Schaltet den ACC-Zeiger-Vorgabemodus wieder aus",
    "ru": "выключить принудительное задание для индикатора ACC",
    "en": "stop forcing the ACC indicator",
    "tags": []
  },
  {
    "name": "STEUERN_VWF",
    "addr": "0x00061105",
    "comment": "Drehzahl fuer DZM-Vorwarnfeld-Zeiger in 1/min vorgeben  (временно, сессия)",
    "ru": "задать произвольные обороты для стрелки предупредительного поля тахометра (зона перед красной зоной) — временно, на время сессии",
    "en": "set an arbitrary rpm for the tachometer pre-warning field (the zone before the red line) — temporary, for the session",
    "tags": []
  },
  {
    "name": "STEUERN_VWF_AUS",
    "addr": "0x00062001",
    "comment": "Schaltet den VWF-Zeiger-Vorgabemodus wieder aus",
    "ru": "выключить принудительное задание оборотов предупредительного поля",
    "en": "stop forcing the pre-warning field rpm",
    "tags": []
  },
  {
    "name": "STATUS_TANKINHALT",
    "addr": "0x000623AB",
    "comment": "Literwerte der Tank-Hebelgeber 1 und 2,",
    "ru": "прочитать \"сырые\" значения уровня топлива от обоих датчиков-поплавков (1 и 2) в литрах",
    "en": "read the raw fuel level of both float sensors (1 and 2) in litres",
    "tags": []
  },
  {
    "name": "STATUS_A_TEMP_LESEN",
    "addr": "0x00062D56",
    "comment": "A-Temp, Anzeige und Rohwert lesen",
    "ru": "прочитать температуру воздуха снаружи: и отображаемое значение, и необработанное (сырое) с датчика",
    "en": "read the outside air temperature: both the displayed and the raw sensor value",
    "tags": []
  },
  {
    "name": "GWSZ_RESET",
    "addr": "0x0006340D",
    "comment": "GWSZ Korrektur-Offset aendern",
    "ru": "изменить корректирующее смещение одометра (GWSZ — \"скорректированный общий пробег\")",
    "en": "change the odometer correction offset (GWSZ — \"corrected total mileage\")",
    "tags": []
  },
  {
    "name": "STATUS_ABSOLUTER_GWSZ",
    "addr": "0x00063D28",
    "comment": "liefert den absoluten GWSZ",
    "ru": "прочитать абсолютный (несмещённый) пробег",
    "en": "read the absolute (unshifted) mileage",
    "tags": []
  },
  {
    "name": "STATUS_GWSZ_OFFSET",
    "addr": "0x0006440C",
    "comment": "liefert den GWSZ-Offset",
    "ru": "прочитать текущее смещение пробега (разницу между абсолютным и отображаемым значением)",
    "en": "read the current mileage offset (difference between absolute and displayed)",
    "tags": []
  },
  {
    "name": "STATUS_GWSZ_ANZEIGE",
    "addr": "0x000648AB",
    "comment": "liefert den angezeigeten GWSZ",
    "ru": "прочитать пробег, который реально показывается на одометре (с учётом смещения)",
    "en": "read the mileage actually shown on the odometer (offset applied)",
    "tags": []
  },
  {
    "name": "LESEN_AKTUELLES_UIF",
    "addr": "0x000651FA",
    "comment": "aktuelles UIF lesen",
    "ru": "прочитать текущее \"поле информации пользователя\" (UIF) щитка",
    "en": "read the cluster's current \"user information field\" (UIF)",
    "tags": []
  },
  {
    "name": "LESEN_HW_NUMMER",
    "addr": "0x00065B73",
    "comment": "HW-Nummer lesen",
    "ru": "прочитать номер аппаратной версии (HW-Nummer) щитка",
    "en": "read the cluster hardware version number (HW-Nummer)",
    "tags": []
  },
  {
    "name": "LESEN_EEPROM_DATENINDEX",
    "addr": "0x00066236",
    "comment": "EEPROM-Datenindex lesen",
    "ru": "прочитать индекс (версию) набора данных в EEPROM",
    "en": "read the index (version) of the data set in EEPROM",
    "tags": []
  },
  {
    "name": "LESEN_VARIANTENINDEX",
    "addr": "0x0006679D",
    "comment": "Variantenindex lesen",
    "ru": "прочитать индекс варианта (конкретной модификации/комплектации) щитка",
    "en": "read the variant index (the specific cluster version/equipment)",
    "tags": []
  },
  {
    "name": "LESEN_HW_AENDERUNGSINDEX",
    "addr": "0x00066C12",
    "comment": "Hardware-Aenderungsindex lesen",
    "ru": "прочитать индекс аппаратных изменений (ревизию платы/железа)",
    "en": "read the hardware change index (board/hardware revision)",
    "tags": []
  },
  {
    "name": "LESEN_DIAGNOSEINDEX",
    "addr": "0x00067233",
    "comment": "Diagnoseindex lesen",
    "ru": "прочитать индекс версии диагностического ПО щитка",
    "en": "read the diagnostic software version index",
    "tags": []
  },
  {
    "name": "LESEN_FERTIGUNGSDATUM",
    "addr": "0x00067696",
    "comment": "Fertigungsdatum lesen",
    "ru": "прочитать дату изготовления щитка",
    "en": "read the cluster's manufacturing date",
    "tags": []
  },
  {
    "name": "LESEN_LIEFEREANTENNUMMER",
    "addr": "0x000681A1",
    "comment": "Lieferantennummer lesen",
    "ru": "прочитать номер поставщика (производителя щитка — Siemens VDO/Johnson Controls и т.п.)",
    "en": "read the supplier number (cluster manufacturer — Siemens VDO/Johnson Controls etc.)",
    "tags": []
  },
  {
    "name": "LESEN_SW_LAYER_VERSION",
    "addr": "0x0006860E",
    "comment": "SW-Layer Versionen lesen",
    "ru": "прочитать версии программных \"слоёв\" (внутренних модулей прошивки)",
    "en": "read the versions of the software \"layers\" (internal firmware modules)",
    "tags": []
  },
  {
    "name": "STATUS_TACHO_LESEN",
    "addr": "0x000692C5",
    "comment": "gibt die Anzeigegeschwindigleit aus (Einheit km/h)",
    "ru": "прочитать текущую отображаемую скорость (км/ч) — обычное чтение, в отличие от `STEUERN_TACHO`, которое её задаёт",
    "en": "read the currently displayed speed (km/h) — a plain read, unlike `STEUERN_TACHO`, which sets it",
    "tags": []
  },
  {
    "name": "STATUS_DREHZAHL_LESEN",
    "addr": "0x000697C6",
    "comment": "gibt die Motordrehzahl aus (Einheit Umdrehungen/min)",
    "ru": "прочитать текущие обороты двигателя (об/мин)",
    "en": "read the current engine speed (rpm)",
    "tags": []
  },
  {
    "name": "STATUS_LENKSTOCK",
    "addr": "0x00069CAC",
    "comment": "gibt den Status des Lenkstockschalters aus",
    "ru": "прочитать состояние подрулевого переключателя (какие кнопки/положения активны)",
    "en": "read the steering column stalk state (which buttons/positions are active)",
    "tags": []
  },
  {
    "name": "STATUS_KL30_H_OFFSET",
    "addr": "0x0006A311",
    "comment": "Klemme 30 Stundenzaehler Offset auslesen",
    "ru": "прочитать смещение счётчика часов работы по клемме 30 (постоянное питание)",
    "en": "read the offset of the terminal-30 (permanent power) operating hours counter",
    "tags": []
  },
  {
    "name": "STATUS_KL30_H_ZAEHLER",
    "addr": "0x0006A857",
    "comment": "Klemme 30 Stundenzaehler auslesen",
    "ru": "прочитать сам счётчик часов работы по клемме 30",
    "en": "read the terminal-30 operating hours counter itself",
    "tags": []
  },
  {
    "name": "CALC_KL30_H_OFFSET",
    "addr": "0x0006ADA1",
    "comment": "Klemme 30 Stundenzaehler Offset ab dem momentanen Datum berechnen",
    "ru": "рассчитать смещение счётчика часов клеммы 30 от текущей даты",
    "en": "compute the terminal-30 hours offset from the current date",
    "tags": []
  },
  {
    "name": "SET_KL30_OFFSET2AKT_DATE",
    "addr": "0x0006BC1C",
    "comment": "Berechnet den Klemme 30 Stundenzaehler Offset ab dem momentanen Datum",
    "ru": "применить рассчитанное смещение счётчика часов клеммы 30 к текущей дате",
    "en": "apply the computed terminal-30 hours offset to the current date",
    "tags": []
  },
  {
    "name": "STATUS_DATE_LAST_CODING_SESSION",
    "addr": "0x0006CDDF",
    "comment": "Datum, gibt an, wann das Kombi zum letzten mal codiert wurde (bei BMW)  **[CODING, read-only]**",
    "ru": "прочитать дату, когда щиток последний раз кодировался на заводе/у BMW (только чтение, менять нельзя)",
    "en": "read the date the cluster was last coded at the factory/BMW (read-only)",
    "tags": []
  },
  {
    "name": "STATUS_KLEMMEN",
    "addr": "0x0006D588",
    "comment": "Klemmenstati auslesen",
    "ru": "прочитать состояние клемм зажигания (30/15/X и т.п. — что сейчас запитано)",
    "en": "read the ignition terminal states (30/15/X etc. — what is powered right now)",
    "tags": []
  },
  {
    "name": "C_FG_LESEN2",
    "addr": "0x0006DC31",
    "comment": "Fahrgestellnummer lesen",
    "ru": "альтернативный/резервный джоб чтения VIN (дублирует `C_FG_LESEN`)",
    "en": "alternative/backup VIN read job (duplicates `C_FG_LESEN`)",
    "tags": [
      "CODING"
    ]
  },
  {
    "name": "STATUS_KLEMMENSPANNUNG",
    "addr": "0x0006E0A2",
    "comment": "liefert Wert der Kombi-Versorgungsspannung",
    "ru": "прочитать напряжение питания щитка (бортовая сеть)",
    "en": "read the cluster supply voltage (vehicle electrical system)",
    "tags": []
  },
  {
    "name": "STATUS_CHECKCONTROL_LESEN",
    "addr": "0x0006E5A1",
    "comment": "gibt die ID Nummern der momentan aktiven CC-Meldungen aus",
    "ru": "прочитать ID-номера сообщений Check Control, активных прямо сейчас",
    "en": "read the IDs of the Check Control messages active right now",
    "tags": []
  },
  {
    "name": "STATUS_BETRIEBSDATEN_HEADER",
    "addr": "0x0006EF1C",
    "comment": "gibt den KM Stand aus CBS Betriebsdaten Header aus",
    "ru": "прочитать пробег из заголовка эксплуатационных данных CBS",
    "en": "read the mileage from the CBS operating data header",
    "tags": []
  },
  {
    "name": "STATUS_BETRIEBSDATEN_LESEN",
    "addr": "0x000702C1",
    "comment": "liest ausgewaehlte Daten aus CBS Betriebsdaten aus",
    "ru": "прочитать выбранные эксплуатационные данные CBS (детали по интервалам обслуживания)",
    "en": "read selected CBS operating data (service interval details)",
    "tags": []
  },
  {
    "name": "STATUS_ZEITSTRAHL",
    "addr": "0x00071854",
    "comment": "gibt CBS Daten fuer den Annahmerechner in der Reihenfolge Header",
    "ru": "выдать данные CBS \"по временной шкале\" для сервисного калькулятора приёмки (когда что нужно обслужить)",
    "en": "output CBS data \"on a timeline\" for the service advisor's calculator (what needs service when)",
    "tags": []
  },
  {
    "name": "STEUERN_CBS_KM_PER_YEAR",
    "addr": "0x0007295C",
    "comment": "Vorgabe Km/Jahr fuer CBS",
    "ru": "задать среднегодовой пробег для расчётов CBS (сервисных интервалов)",
    "en": "set the average annual mileage used for CBS calculations",
    "tags": []
  },
  {
    "name": "STEUERN_CBS_SC_CODIERUNG",
    "addr": "0x00072DE5",
    "comment": "CBS Servicecall Enable/Disable Codierung.  **[CODING-подобный]**",
    "ru": "включить/выключить кодирование service-call для CBS (похоже на коддинг, но отдельный механизм)",
    "en": "enable/disable service-call coding for CBS (coding-like, but a separate mechanism)",
    "tags": []
  },
  {
    "name": "STATUS_CBS_WOCHEN_KM",
    "addr": "0x0007410D",
    "comment": "gibt die Daten des KM pro Woche-Algorithmus aus CBS Betriebsdaten Header aus",
    "ru": "прочитать данные алгоритма \"км в неделю\" из заголовка эксплуатационных данных CBS",
    "en": "read the \"km per week\" algorithm data from the CBS operating data header",
    "tags": []
  },
  {
    "name": "MOTORTYP",
    "addr": "0x0007541D",
    "comment": "im Kombi codierter Motortyp ermitteln",
    "ru": "определить тип двигателя, закодированный в щитке (из коддинг-данных)",
    "en": "determine the engine type coded into the cluster (from coding data)",
    "tags": []
  },
  {
    "name": "STEUERN_TESTBITMAP",
    "addr": "0x000774AE",
    "comment": "Testbitmap im Display darstellen",
    "ru": "вывести тестовое изображение (битмап) на экран щитка — удобно для проверки всех пикселей/сегментов сразу",
    "en": "show a test image (bitmap) on the cluster display — handy for checking every pixel/segment at once",
    "tags": []
  },
  {
    "name": "STEUERN_TESTBITMAP_AUS",
    "addr": "0x00077A7B",
    "comment": "Testbitmap im Display wieder abschalten",
    "ru": "убрать тестовое изображение, вернуть обычный экран",
    "en": "remove the test image, back to the normal screen",
    "tags": []
  },
  {
    "name": "STATUS_CHECKCONTROL_HISTORY",
    "addr": "0x00077E25",
    "comment": "CC-Meldungsspeicher aus Kombi lesen",
    "ru": "прочитать историю (архив) сообщений Check Control из памяти щитка",
    "en": "read the history (archive) of Check Control messages from cluster memory",
    "tags": []
  },
  {
    "name": "ZEIGERZAHL",
    "addr": "0x000785FE",
    "comment": "Ermittelt aus den Codierdaten die Anzahl der im Kombi",
    "ru": "определить по коддинг-данным количество реальных стрелок в щитке (разные комплектации — разное число приборов)",
    "en": "determine from coding data how many real needles the cluster has (different versions have different gauges)",
    "tags": []
  },
  {
    "name": "STATUS_BOS_CODIERUNG",
    "addr": "0x0007B2F3",
    "comment": "CBS Codierung fuer alle einzelnen CBS Groessen.  **[CODING-подобный]**",
    "ru": "прочитать коддинг CBS по каждому отдельному показателю обслуживания (масло, тормоза и т.д.)",
    "en": "read the CBS coding for each individual service item (oil, brakes etc.)",
    "tags": []
  },
  {
    "name": "STEUERN_BOS_CODIERUNG",
    "addr": "0x0007BB31",
    "comment": "CBS Codierung fuer alle einzelnen CBS Groessen.  **[CODING-подобный]**",
    "ru": "записать коддинг CBS по каждому отдельному показателю обслуживания",
    "en": "write the CBS coding for each individual service item",
    "tags": []
  },
  {
    "name": "STATUS_GLOBAL_KM",
    "addr": "0x0007CECD",
    "comment": "liest den GWSZ aus KI RAM, EEPROM & CAS",
    "ru": "прочитать пробег сразу из трёх источников — RAM щитка, EEPROM и блока CAS — для сверки",
    "en": "read the mileage from three sources at once — cluster RAM, EEPROM and the CAS module — for cross-checking",
    "tags": []
  },
  {
    "name": "STATUS_KI",
    "addr": "0x0007DF20",
    "comment": "Liest Block.",
    "ru": "прочитать произвольный блок данных щитка (служебный, параметр \"какой блок\" передаётся отдельно)",
    "en": "read an arbitrary cluster data block (service job, the block is passed as a parameter)",
    "tags": []
  },
  {
    "name": "RINGBUF_INIT",
    "addr": "0x0007E356",
    "comment": "Initialisiert den Ringbuffer",
    "ru": "инициализировать кольцевой буфер (сбросить служебную очередь записей перед её использованием)",
    "en": "initialise the ring buffer (reset the service record queue before use)",
    "tags": []
  },
  {
    "name": "LESEN_RINGBUF",
    "addr": "0x0007E6FF",
    "comment": "Liest den Ringbuffer Inhalt",
    "ru": "прочитать содержимое кольцевого буфера",
    "en": "read the ring buffer contents",
    "tags": []
  },
  {
    "name": "STATUS_NTC1",
    "addr": "0x0007F033",
    "comment": "Liefert den ADC-Wert von Kanal 3 (NTC1)",
    "ru": "прочитать \"сырое\" значение АЦП с канала 3 (термистор NTC1 — один из температурных датчиков щитка)",
    "en": "read the raw ADC value of channel 3 (thermistor NTC1 — one of the cluster's temperature sensors)",
    "tags": []
  },
  {
    "name": "LESEN_CODIERBLOCK",
    "addr": "0x0007F492",
    "comment": "Codierdatenblock aus EEPROM auslesen  **[CODING, низкоуровневый]**",
    "ru": "низкоуровневое чтение блока коддинга прямо из EEPROM (ещё более низкий уровень, чем `CODIERDATEN_LESEN`)",
    "en": "low-level coding block read straight from EEPROM (even lower level than `CODIERDATEN_LESEN`)",
    "tags": []
  },
  {
    "name": "RESTORE_PIA_DEFAULT",
    "addr": "0x0007FB87",
    "comment": "PIA Schluesselwerte mit Defaultschluesselwerten ueberschreiben",
    "ru": "сбросить ключи PIA (защищённый доступ/аутентификация) на заводские значения по умолчанию",
    "en": "reset the PIA keys (protected access/authentication) to factory defaults",
    "tags": []
  },
  {
    "name": "LESEN_PIA_WERTE",
    "addr": "0x00081496",
    "comment": "PIA Schluesselwerte auslesen",
    "ru": "прочитать текущие значения ключей PIA",
    "en": "read the current PIA key values",
    "tags": []
  },
  {
    "name": "STEUERN_CCG",
    "addr": "0x00084B26",
    "comment": "CC Gong ausloesen",
    "ru": "принудительно включить звуковой сигнал Check Control (гонг) — сервисная проверка звука",
    "en": "force the Check Control chime (gong) — service sound check",
    "tags": []
  },
  {
    "name": "STEUERGERAETE_RESET_DELAY",
    "addr": "0x00084ED0",
    "comment": "Seuergeraete reset mit Delay ausloesen",
    "ru": "перезагрузить блок с задержкой (не мгновенно, как обычный `STEUERGERAETE_RESET`)",
    "en": "reboot the module with a delay (not instantly like `STEUERGERAETE_RESET`)",
    "tags": []
  },
  {
    "name": "STEUERN_ATEMP_RESET",
    "addr": "0x000857FF",
    "comment": "A-Temp-Berechnung zurücksetzen (den Rohwert in die Anzeige übernehmen)",
    "ru": "сбросить алгоритм расчёта температуры воздуха (перенести \"сырое\" значение сразу в отображаемое, без сглаживания)",
    "en": "reset the outside temperature algorithm (copy the raw value straight to the displayed one, no smoothing)",
    "tags": []
  },
  {
    "name": "LESEN_HW_AENDERUNGSINDEX_PRODUKTIONSORT",
    "addr": "0x00085BA8",
    "comment": "Hardware-Aenderungsindex lesen",
    "ru": "прочитать индекс аппаратных изменений с учётом места производства (альтернативный вариант `LESEN_HW_AENDERUNGSINDEX`)",
    "en": "read the hardware change index including the production site (alternative to `LESEN_HW_AENDERUNGSINDEX`)",
    "tags": []
  },
  {
    "name": "STATUS_CBS_ANZEIGE",
    "addr": "0x00086600",
    "comment": "",
    "ru": "прочитать, что именно сейчас показывается на экране по сервисным интервалам CBS",
    "en": "read what is currently shown on the display for CBS service intervals",
    "tags": []
  },
  {
    "name": "STEUERN_ANPASSEN_ACC_KENNLINIE_SVDO",
    "addr": "0x00087363",
    "comment": "DATENSATZ anpassen  (калибровка кривой стрелки ACC, NVRAM, без подписи)",
    "ru": "откалибровать характеристику (кривую) стрелки/индикатора ACC — пишет в NVRAM напрямую, без крипто-подписи",
    "en": "calibrate the characteristic curve of the ACC needle/indicator — writes NVRAM directly, no crypto signature",
    "tags": []
  },
  {
    "name": "STEUERN_ANPASSEN_LCD_KENNLINIE_SVDO",
    "addr": "0x00089BDF",
    "comment": "DATENSATZ anpassen  (калибровка кривой LCD-стрелки, NVRAM, без подписи)",
    "ru": "откалибровать характеристику (кривую) LCD-индикатора — пишет в NVRAM напрямую, без крипто-подписи",
    "en": "calibrate the characteristic curve of the LCD indicator — writes NVRAM directly, no crypto signature",
    "tags": []
  }
];
