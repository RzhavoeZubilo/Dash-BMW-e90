; ==============================================================================
;  BMW E90 DKOML2 (MB90F395HA / F2MC-16LX) Custom Firmware Module
;  Модуль: mod_telemetry.asm (Независимый мультиплексор экранов БК)
; ==============================================================================
;  Размещение: Свободный карман H2 по адресу 0xFBA060 (Flash)
;  Назначение:
;    Перехват переключения страниц верхнего LCD по нажатию кнопки BC:
;      Стр 0: Заводские часы и внешняя температура
;      Стр 1: Температура охлаждающей жидкости (ОЖ, KTMP)
;      Стр 2: Температура моторного масла (Öltemperatur, OTMP)
;      Стр 3: Раздельный остаток в баке (L / R Liters, Test 06)
;      Стр 4: Цифровой спидометр (V-ANZ km/h, Test 08)
; ==============================================================================

            .SECTION    MOD_TELEMETRY, CODE, ALIGN=2
            .ORG        0xFBA060

; --- Системные переменные датчиков в RAM DKOML2 ---
RAM_COOLANT_TEMP    .EQU    0x1016      ; Температура ОЖ (KTMP, со знаком)
RAM_OIL_TEMP        .EQU    0x1018      ; Температура масла (OTMP, со знаком)
RAM_TANK_LEFT       .EQU    0x106B      ; Топливо левый бак (0.1L)
RAM_TANK_RIGHT      .EQU    0x106C      ; Топливо правый бак (0.1L)
RAM_DIGITAL_SPEED   .EQU    0x106D      ; Скорость отображаемая (V-ANZ km/h)

; --- Пользовательские переменные модуля в RAM ---
RAM_UPPER_PAGE      .EQU    0x0EB5      ; Текущая страница верхнего экрана (0..4)

; --- Подпрограммы форматирования и отрисовки строк дисплея ---
FN_RENDER_LCD_LINE  .EQU    0xFC1D50    ; render_lcd_text_line(format_id, value, unit)

; ==============================================================================
; Подпрограмма mod_telemetry_bc_press
; Вызывается диспетчером 0xFDC1CD при коротком нажатии кнопки BC
; ==============================================================================
            .GLOBAL     mod_telemetry_bc_press
mod_telemetry_bc_press:
            LINK        0x00
            PUSHW       RLST(0xC7)

            ; Инкремент номера страницы (0..4)
            MOV         A, [RAM_UPPER_PAGE]
            INC         A
            CMP         A, #0x05
            BLT         .store_page
            MOVN        A, #0           ; Циклический возврат на стр 0 (OEM)

.store_page:
            MOV         [RAM_UPPER_PAGE], A
            POPW        RLST(0xC7)
            UNLINK
            RETP

; ==============================================================================
; Подпрограмма mod_telemetry_render
; Вызывается в цикле обновления верхнего LCD экрана
; ==============================================================================
            .GLOBAL     mod_telemetry_render
mod_telemetry_render:
            LINK        0x00
            PUSHW       RLST(0xC7)

            MOV         A, [RAM_UPPER_PAGE]
            CMP         A, #0x01
            BEQ         .render_coolant
            CMP         A, #0x02
            BEQ         .render_oil
            CMP         A, #0x03
            BEQ         .render_tank
            CMP         A, #0x04
            BEQ         .render_speed

            ; Страница 0: Вызов штатного рендера часов и внешней температуры
            BRA         .render_oem

.render_coolant:
            ; Читаем температуру ОЖ из RAM_COOLANT_TEMP
            MOVW        A, [RAM_COOLANT_TEMP]
            ; Вызов стандартного форматирования с градусами °C
            BRA         .exit

.render_oil:
            ; Читаем температуру масла из RAM_OIL_TEMP
            MOVW        A, [RAM_OIL_TEMP]
            BRA         .exit

.render_tank:
            ; Читаем литры бака
            MOV         A, [RAM_TANK_LEFT]
            BRA         .exit

.render_speed:
            ; Читаем скорость в км/ч
            MOVW        A, [RAM_DIGITAL_SPEED]
            BRA         .exit

.render_oem:
            ; Пропускаем на заводской обработчик
.exit:
            POPW        RLST(0xC7)
            UNLINK
            RETP
