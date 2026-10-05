# komb87.prg -- full job list (133 jobs)

Source: BMW SP-Daten 69.0/BASE/ecu/komb87.prg
Decoded with decoderPrg.py (BimmerDis port, from /Users/densh/Work/Develop/symfony/BimmerDaten).

## All jobs (name @ address, first comment line)

- `INFO` @ 0x000000A0 -- Information SGBD
- `INITIALISIERUNG` @ 0x000001FF -- Initialisierung und Kommunikationsparameter
- `DIAGNOSEPROTOKOLL_LESEN` @ 0x0000276E -- Gibt die möglichen Diagnoseprotokolle
- `DIAGNOSEPROTOKOLL_SETZEN` @ 0x00002C24 -- Wählt ein Diagnoseprotokoll aus
- `IDENT` @ 0x00002E8B -- Identdaten
- `FS_LESEN` @ 0x00005443 -- Fehlerspeicher lesen (alle Fehler / Ort und Art)
- `FS_LESEN_DETAIL` @ 0x000074E2 -- Fehlerspeicher lesen (ein Fehler / alle Details)
- `FS_LOESCHEN` @ 0x000119B7 -- Fehlerspeicher loeschen
- `PRUEFSTEMPEL_LESEN` @ 0x000126B4 -- Auslesen des Pruefstempels
- `PRUEFSTEMPEL_SCHREIBEN` @ 0x00013417 -- Beschreiben des Pruefstempels
- `NORMALER_DATENVERKEHR` @ 0x0001452E -- Sperren bzw. Freigeben des normalen Datenverkehrs
- `DIAGNOSE_AUFRECHT` @ 0x0001638A -- Diagnosemode des SG aufrecht erhalten
- `DIAGNOSE_ENDE` @ 0x00017F80 -- Diagnosemode des SG beenden
- `DIAGNOSE_MODE` @ 0x000187DB -- SG in bestimmten Diagnosemode bringen
- `SLEEP_MODE` @ 0x000195DA -- SG in Sleep-Mode versetzen
- `ENERGIESPARMODE` @ 0x0001A31F -- Einstellen des Energiesparmodes
- `SPEICHER_LESEN` @ 0x0001B274 -- Auslesen des Steuergeraete-Speichers
- `SPEICHER_SCHREIBEN` @ 0x0001C6D6 -- Beschreiben des Steuergeraete-Speichers
- `CBS_INFO` @ 0x0001E282 -- Ausgabe der CBS-Version
- `CBS_DATEN_LESEN` @ 0x0001E6C2 -- CBS Daten auslesen (fuer CBS-Version 4)
- `CBS_RESET` @ 0x0002584B -- CBS Daten Zuruecksetzen (fuer CBS-Version 4)
- `PRUEFCODE_LESEN` @ 0x0002757E -- Standard Pruefcode lesen fuer Kundendienst
- `C_CI_LESEN` @ 0x0002906C -- Codierindex lesen  **[CODING]**
- `C_FG_LESEN` @ 0x0002AF48 -- Fahrgestellnummer lesen  **[CODING]**
- `C_FG_SCHREIBEN` @ 0x0002C0B1 -- Fahrgestellnummer schreiben  **[CODING]**
- `C_FG_AUFTRAG` @ 0x0002D320 -- Fahrgestellnummer schreiben und ruecklesen  **[CODING]**
- `C_AEI_LESEN` @ 0x0002F32C -- Aenderungsindex der Codierdaten lesen  **[CODING]**
- `C_AEI_SCHREIBEN` @ 0x000305BE -- Aenderungsindex der Codierdaten schreiben  **[CODING]**
- `C_AEI_AUFTRAG` @ 0x0003195B -- Aenderungsindex der Codierdaten schreiben und ruecklesen  **[CODING]**
- `C_C_LESEN` @ 0x00033A48 -- Codierdaten lesen  **[CODING]**
- `C_C_SCHREIBEN` @ 0x00034ECF -- Codierdaten schreiben  **[CODING -- главный джоб NCS Expert]**
- `C_C_AUFTRAG` @ 0x00036384 -- Codierdaten schreiben und ruecklesen  **[CODING]**
- `SERIENNUMMER_LESEN` @ 0x000386FD -- Hersteller Seriennummer lesen
- `ZIF_LESEN` @ 0x00039B9A -- Auslesen des Zulieferinfofeldes
- `ZIF_BACKUP_LESEN` @ 0x0003C7F7 -- Auslesen des Backups des Zulieferinfofeldes
- `PHYSIKALISCHE_HW_NR_LESEN` @ 0x0003E3D0 -- Auslesen der physikalischen Hardwarenummer
- `HARDWARE_REFERENZ_LESEN` @ 0x0003F985 -- Auslesen der Hardware Referenz
- `DATEN_REFERENZ_LESEN` @ 0x00040FF1 -- Auslesen der Daten Referenz
- `FLASH_ZEITEN_LESEN` @ 0x00041F71 -- Auslesen der Flash Loeschzeit, Signaturtestzeit,
- `FLASH_BLOCKLAENGE_LESEN` @ 0x00042E2E -- Auslesen des maximalen Blocklaenge beim Flashen
- `AUTHENTISIERUNG_ZUFALLSZAHL_LESEN` @ 0x0004390A -- Authentisierung Zufallszahl des SG lesen  **[FIRMWARE]**
- `AUTHENTISIERUNG_START` @ 0x000446AD -- Authentisierung pruefen  **[FIRMWARE]**
- `FLASH_PROGRAMMIER_STATUS_LESEN` @ 0x00046502 -- Programmierstatus des SG lesen  **[FIRMWARE]**
- `FLASH_SIGNATUR_PRUEFEN` @ 0x0004705E -- Flash Signatur pruefen  **[FIRMWARE]**
- `STEUERGERAETE_RESET` @ 0x00048B74 -- Steuergeraete reset ausloesen
- `FLASH_LOESCHEN` @ 0x000493D0 -- Flash loeschen  **[FIRMWARE]**
- `FLASH_SCHREIBEN_ADRESSE` @ 0x0004B1EB -- Vorbereitung fuer Flash schreiben  **[FIRMWARE]**
- `FLASH_SCHREIBEN` @ 0x0004C0B2 -- Flash Daten schreiben  **[FIRMWARE]**
- `FLASH_SCHREIBEN_ENDE` @ 0x0004D01F -- Flashprogrammierung abschliessen  **[FIRMWARE]**
- `AIF_LESEN` @ 0x0004DD1C -- Auslesen des Anwender Informations Feldes
- `AIF_SCHREIBEN` @ 0x00050874 -- Schreiben des Anwender Informations Feldes
- `SG_RESET_OHNE_UHR_DATUM` @ 0x00054EF7 -- Steuergeraete Reset ausloesen
- `UHRZEIT_DATUM_STELLEN` @ 0x000552A0 -- Uhrzeit und Datum stellen
- `CODIERDATEN_LESEN` @ 0x00055FFA  **[CODING]** (чтение блока 0x3000-0x3FFF по номеру блока)
- `C_CHECKSUMME` @ 0x0005665A -- Checksumme generieren und in BINAER_BUFFER schreiben  **[CODING -- считает контрольную сумму блока коддинга]**
- `STEUERN_LEUCHTEN` @ 0x00056DAA -- Kontrolleuchten im Kombi ansteuern
- `STEUERN_LEUCHTEN_BLAU` @ 0x000581A0 -- Blaue Leuchten im Kombi ansteuern
- `STEUERN_LEUCHTEN_GELB` @ 0x0005854E -- Gelbe Leuchten im Kombi ansteuern
- `STEUERN_LEUCHTEN_GRUEN` @ 0x000588FC -- Gruene Leuchten im Kombi ansteuern
- `STEUERN_LEUCHTEN_ORANGE` @ 0x0005902C -- Gelbe Leuchten im Kombi ansteuern
- `STEUERN_LEUCHTEN_ROT` @ 0x000593DA -- Rote Leuchten im Kombi ansteuern
- `STEUERN_LEUCHTEN_AUS` @ 0x00059788 -- Wenn vorher der Job STEUERN_LEUCHTEN aufgerufen wurde
- `STEUERN_BLINKER` @ 0x00059EB2 -- Blinker ansteuern, fuer Service-und Testzwecke
- `STEUERN_BLINKER_AUS` @ 0x0005A673 -- Wenn vorher der Job STEUERN_BLINKER aufgerufen wurde
- `STEUERN_SELBSTTEST_EIN` @ 0x0005AA1D -- Schaltet den Selbttest ein
- `STEUERN_SELBSTTEST_AUS` @ 0x0005B02E -- Schaltet den Selbsttest wieder aus
- `STEUERN_TACHO` @ 0x0005B3D8 -- Tacho auf beliebige Geschwindigkeit (0..300) setzen  (временно, сессия)
- `STEUERN_TACHO_AUS` @ 0x0005C1BF -- Schaltet den Tacho-Vorgabemodus wieder aus
- `STEUERN_DREHZAHL` @ 0x0005C569 -- DrehZahlMesser in 1/min vorgeben  (временно, сессия)
- `STEUERN_DREHZAHL_AUS` @ 0x0005D3C3 -- Schaltet den DZM-Vorgabemodus wieder aus
- `STEUERN_KVA` @ 0x0005D76D -- Momentanverbrauch in L/100km vorgeben  (временно, сессия)
- `STEUERN_KVA_AUS` @ 0x0005E8E4 -- Schaltet den KVA-Vorgabemodus wieder aus
- `STEUERN_TANK` @ 0x0005EC8E -- Tankinhalt in % vorgeben
- `STEUERN_TANK_AUS` @ 0x0005F951 -- Schaltet den Tank-Vorgabemodus wieder aus
- `STEUERN_ACC_ZEIGER` @ 0x0005FCFB -- Geschwindigkeit fuer ACC-Zeiger in km/h vorgeben  (временно, сессия)
- `STEUERN_ACC_ZEIGER_AUS` @ 0x00060D5B -- Schaltet den ACC-Zeiger-Vorgabemodus wieder aus
- `STEUERN_VWF` @ 0x00061105 -- Drehzahl fuer DZM-Vorwarnfeld-Zeiger in 1/min vorgeben  (временно, сессия)
- `STEUERN_VWF_AUS` @ 0x00062001 -- Schaltet den VWF-Zeiger-Vorgabemodus wieder aus
- `STATUS_TANKINHALT` @ 0x000623AB -- Literwerte der Tank-Hebelgeber 1 und 2,
- `STATUS_A_TEMP_LESEN` @ 0x00062D56 -- A-Temp, Anzeige und Rohwert lesen
- `GWSZ_RESET` @ 0x0006340D -- GWSZ Korrektur-Offset aendern
- `STATUS_ABSOLUTER_GWSZ` @ 0x00063D28 -- liefert den absoluten GWSZ
- `STATUS_GWSZ_OFFSET` @ 0x0006440C -- liefert den GWSZ-Offset
- `STATUS_GWSZ_ANZEIGE` @ 0x000648AB -- liefert den angezeigeten GWSZ
- `LESEN_AKTUELLES_UIF` @ 0x000651FA -- aktuelles UIF lesen
- `LESEN_HW_NUMMER` @ 0x00065B73 -- HW-Nummer lesen
- `LESEN_EEPROM_DATENINDEX` @ 0x00066236 -- EEPROM-Datenindex lesen
- `LESEN_VARIANTENINDEX` @ 0x0006679D -- Variantenindex lesen
- `LESEN_HW_AENDERUNGSINDEX` @ 0x00066C12 -- Hardware-Aenderungsindex lesen
- `LESEN_DIAGNOSEINDEX` @ 0x00067233 -- Diagnoseindex lesen
- `LESEN_FERTIGUNGSDATUM` @ 0x00067696 -- Fertigungsdatum lesen
- `LESEN_LIEFEREANTENNUMMER` @ 0x000681A1 -- Lieferantennummer lesen
- `LESEN_SW_LAYER_VERSION` @ 0x0006860E -- SW-Layer Versionen lesen
- `STATUS_TACHO_LESEN` @ 0x000692C5 -- gibt die Anzeigegeschwindigleit aus (Einheit km/h)
- `STATUS_DREHZAHL_LESEN` @ 0x000697C6 -- gibt die Motordrehzahl aus (Einheit Umdrehungen/min)
- `STATUS_LENKSTOCK` @ 0x00069CAC -- gibt den Status des Lenkstockschalters aus
- `STATUS_KL30_H_OFFSET` @ 0x0006A311 -- Klemme 30 Stundenzaehler Offset auslesen
- `STATUS_KL30_H_ZAEHLER` @ 0x0006A857 -- Klemme 30 Stundenzaehler auslesen
- `CALC_KL30_H_OFFSET` @ 0x0006ADA1 -- Klemme 30 Stundenzaehler Offset ab dem momentanen Datum berechnen
- `SET_KL30_OFFSET2AKT_DATE` @ 0x0006BC1C -- Berechnet den Klemme 30 Stundenzaehler Offset ab dem momentanen Datum
- `STATUS_DATE_LAST_CODING_SESSION` @ 0x0006CDDF -- Datum, gibt an, wann das Kombi zum letzten mal codiert wurde (bei BMW)  **[CODING, read-only]**
- `STATUS_KLEMMEN` @ 0x0006D588 -- Klemmenstati auslesen
- `C_FG_LESEN2` @ 0x0006DC31 -- Fahrgestellnummer lesen  **[CODING]**
- `STATUS_KLEMMENSPANNUNG` @ 0x0006E0A2 -- liefert Wert der Kombi-Versorgungsspannung
- `STATUS_CHECKCONTROL_LESEN` @ 0x0006E5A1 -- gibt die ID Nummern der momentan aktiven CC-Meldungen aus
- `STATUS_BETRIEBSDATEN_HEADER` @ 0x0006EF1C -- gibt den KM Stand aus CBS Betriebsdaten Header aus
- `STATUS_BETRIEBSDATEN_LESEN` @ 0x000702C1 -- liest ausgewaehlte Daten aus CBS Betriebsdaten aus
- `STATUS_ZEITSTRAHL` @ 0x00071854 -- gibt CBS Daten fuer den Annahmerechner in der Reihenfolge Header
- `STEUERN_CBS_KM_PER_YEAR` @ 0x0007295C -- Vorgabe Km/Jahr fuer CBS
- `STEUERN_CBS_SC_CODIERUNG` @ 0x00072DE5 -- CBS Servicecall Enable/Disable Codierung.  **[CODING-подобный]**
- `STATUS_CBS_WOCHEN_KM` @ 0x0007410D -- gibt die Daten des KM pro Woche-Algorithmus aus CBS Betriebsdaten Header aus
- `MOTORTYP` @ 0x0007541D -- im Kombi codierter Motortyp ermitteln
- `STEUERN_TESTBITMAP` @ 0x000774AE -- Testbitmap im Display darstellen
- `STEUERN_TESTBITMAP_AUS` @ 0x00077A7B -- Testbitmap im Display wieder abschalten
- `STATUS_CHECKCONTROL_HISTORY` @ 0x00077E25 -- CC-Meldungsspeicher aus Kombi lesen
- `ZEIGERZAHL` @ 0x000785FE -- Ermittelt aus den Codierdaten die Anzahl der im Kombi
- `STATUS_BOS_CODIERUNG` @ 0x0007B2F3 -- CBS Codierung fuer alle einzelnen CBS Groessen.  **[CODING-подобный]**
- `STEUERN_BOS_CODIERUNG` @ 0x0007BB31 -- CBS Codierung fuer alle einzelnen CBS Groessen.  **[CODING-подобный]**
- `STATUS_GLOBAL_KM` @ 0x0007CECD -- liest den GWSZ aus KI RAM, EEPROM & CAS
- `STATUS_KI` @ 0x0007DF20 -- Liest Block.
- `RINGBUF_INIT` @ 0x0007E356 -- Initialisiert den Ringbuffer
- `LESEN_RINGBUF` @ 0x0007E6FF -- Liest den Ringbuffer Inhalt
- `STATUS_NTC1` @ 0x0007F033 -- Liefert den ADC-Wert von Kanal 3 (NTC1)
- `LESEN_CODIERBLOCK` @ 0x0007F492 -- Codierdatenblock aus EEPROM auslesen  **[CODING, низкоуровневый]**
- `RESTORE_PIA_DEFAULT` @ 0x0007FB87 -- PIA Schluesselwerte mit Defaultschluesselwerten ueberschreiben
- `LESEN_PIA_WERTE` @ 0x00081496 -- PIA Schluesselwerte auslesen
- `STEUERN_CCG` @ 0x00084B26 -- CC Gong ausloesen
- `STEUERGERAETE_RESET_DELAY` @ 0x00084ED0 -- Seuergeraete reset mit Delay ausloesen
- `STEUERN_ATEMP_RESET` @ 0x000857FF -- A-Temp-Berechnung zurücksetzen (den Rohwert in die Anzeige übernehmen)
- `LESEN_HW_AENDERUNGSINDEX_PRODUKTIONSORT` @ 0x00085BA8 -- Hardware-Aenderungsindex lesen
- `STATUS_CBS_ANZEIGE` @ 0x00086600
- `STEUERN_ANPASSEN_ACC_KENNLINIE_SVDO` @ 0x00087363 -- DATENSATZ anpassen  (калибровка кривой стрелки ACC, NVRAM, без подписи)
- `STEUERN_ANPASSEN_LCD_KENNLINIE_SVDO` @ 0x00089BDF -- DATENSATZ anpassen  (калибровка кривой LCD-стрелки, NVRAM, без подписи)

## Итог: три разных класса джобов

1. **NCS Expert коддинг (FSW/PSW)** -- отдельная, самостоятельная группа джобов
   `C_C_LESEN`/`C_C_SCHREIBEN`/`C_C_AUFTRAG` (главные), плюс вспомогательные
   `C_CI_LESEN`, `C_FG_*`, `C_AEI_*`, `CODIERDATEN_LESEN`, `LESEN_CODIERBLOCK`,
   `C_CHECKSUMME`. Работают через KWP2000 `$22`/`$2E` (ReadDataByCommonIdentifier /
   WriteDataByCommonIdentifier) на диапазон идентификаторов `$3000-$3EFF`
   (CodingDataSet) -- это НЕ SPEICHER_LESEN/SPEICHER_SCHREIBEN и не универсальный
   адресный доступ. `C_C_SCHREIBEN` явно помечен "Standard Codierjob" -- это и есть
   тот самый механизм, которым пишет NCS Expert.
   Перед записью коддинга считается **контрольная сумма** (джоб `C_CHECKSUMME`,
   "Optionaler Codierjob") -- это просто checksum над буфером, а не крипто-подпись.

2. **SPEICHER_LESEN / SPEICHER_SCHREIBEN** -- универсальный низкоуровневый доступ
   к памяти по сегменту+адресу (ROMI, ROMX, NVRAM, RAMIS, RAMXX, FLASH, UIFM, VODM,
   FLASHX, RAMIL). Отдельный от коддинга механизм; используется, в частности,
   калибровочными джобами `STEUERN_ANPASSEN_ACC_KENNLINIE_SVDO` /
   `STEUERN_ANPASSEN_LCD_KENNLINIE_SVDO` (пишут в NVRAM, тоже без подписи).

3. **Firmware/Flash** -- `AUTHENTISIERUNG_*`, `FLASH_LOESCHEN`, `FLASH_SCHREIBEN*`,
   `FLASH_SIGNATUR_PRUEFEN`. Единственная группа, где есть challenge-response
   авторизация и криптографическая подпись после записи.
