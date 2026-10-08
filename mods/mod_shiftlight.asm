; ==============================================================================
;  BMW E90 DKOML2 (MB90F395HA / F2MC-16LX) Custom Firmware Module
;  Модуль: mod_shiftlight.asm (Прогрессивный Shift-Light на лампах ACC)
; ==============================================================================
;  Размещение: Свободный карман H2 по адресу 0xFB9FF0 (Flash)
;  Назначение:
;    В ручном режиме АКПП [M] зажигает полоски дистанции ACC в зависимости от RPM:
;      < 4000 RPM  -> все полоски выключены
;      4000..4499  -> 1-я полоска (нижняя)
;      4500..4999  -> 2 полоски
;      5000..5199  -> 3 полоски
;      >= 5200     -> СТРОБОСКОП (все 4 полоски + боковые рельсы на ~10 Гц)
;    Машинка (ID 0x24) принудительно отключена per user specification.
; ==============================================================================

            .SECTION    MOD_SHIFTLIGHT, CODE, ALIGN=2
            .ORG        0xFB9FF0

; --- Точки входа штатных подпрограмм приборки ---
FN_SET_TELLTALE     .EQU    0xFD47ED    ; (state, id) -> управление лампами
FN_SET_ACC_BARS     .EQU    0xFF2843    ; (bar_level, max_bars) -> отрисовка полосок

; --- Идентификаторы ламп ACC ---
ID_ACC_CAR          .EQU    0x24        ; Силуэт автомобиля ACC (не используется)
ID_ACC_ROAD         .EQU    0x25        ; Боковые линии разметки

; --- Буферы оперативной памяти (RAM) DKOML2 ---
RAM_GEAR_CHAR1      .EQU    0x0B2A      ; Первый символ режима ('M', 'D', 'P', 'R')
RAM_BLINK_STATE     .EQU    0x0EB4      ; Свободный байт флага полупериода стробоскопа

; ==============================================================================
; Подпрограмма mod_shiftlight_tick
; Вызывается из основного цикла обработки тахометра CAN 0x0AA
; Вход:  RW0 = Текущие обороты двигателя (RPM) в 1/min
; ==============================================================================
            .GLOBAL     mod_shiftlight_tick
mod_shiftlight_tick:
            LINK        0x00
            PUSHW       RLST(0xC7)      ; Сохранение регистров RW0-RW2, RW4-RW6

            ; 1. Проверяем режим коробки: активен ли ручной режим [M]?
            ;    Символ 'M' имеет ASCII код 0x4D.
            MOV         A, [RAM_GEAR_CHAR1]
            CMP         A, #0x4D
            BNE         .acc_all_off    ; Если не режим 'M' -> гасим полоски

            ; 2. Проверяем пороги оборотов двигателя (входное значение в RW0)
            MOVW        A, RW0

            ; --- Порог 4: Стробоскоп (>= 5200 RPM) ---
            CMPW        A, #5200
            BGE         .stage_strobe

            ; --- Порог 3: 3 полоски (>= 5000 RPM) ---
            CMPW        A, #5000
            BGE         .stage_3_bars

            ; --- Порог 2: 2 полоски (>= 4500 RPM) ---
            CMPW        A, #4500
            BGE         .stage_2_bars

            ; --- Порог 1: 1 полоска (>= 4000 RPM) ---
            CMPW        A, #4000
            BGE         .stage_1_bar

            ; --- Обороты ниже 4000 -> Выключить всё ---
            BRA         .acc_all_off

; ------------------------------------------------------------------------------
; Обработчики ступеней
; ------------------------------------------------------------------------------

.stage_1_bar:
            ; Гасим боковые рельсы (ID 0x25, state 0)
            MOVN        A, #0
            PUSHW       A
            MOV         A, #ID_ACC_ROAD
            PUSHW       A
            CALLP       [FN_SET_TELLTALE]
            ADD         SSP, #0x04

            ; Зажигаем 1 полоску: FN_SET_ACC_BARS(1, 4)
            MOVN        A, #4           ; MAX_BARS = 4
            PUSHW       A
            MOVN        A, #1           ; LEVEL = 1
            PUSHW       A
            CALLP       [FN_SET_ACC_BARS]
            ADD         SSP, #0x04
            BRA         .exit

.stage_2_bars:
            ; Гасим боковые рельсы
            MOVN        A, #0
            PUSHW       A
            MOV         A, #ID_ACC_ROAD
            PUSHW       A
            CALLP       [FN_SET_TELLTALE]
            ADD         SSP, #0x04

            ; Зажигаем 2 полоски: FN_SET_ACC_BARS(2, 4)
            MOVN        A, #4
            PUSHW       A
            MOVN        A, #2           ; LEVEL = 2
            PUSHW       A
            CALLP       [FN_SET_ACC_BARS]
            ADD         SSP, #0x04
            BRA         .exit

.stage_3_bars:
            ; Гасим боковые рельсы
            MOVN        A, #0
            PUSHW       A
            MOV         A, #ID_ACC_ROAD
            PUSHW       A
            CALLP       [FN_SET_TELLTALE]
            ADD         SSP, #0x04

            ; Зажигаем 3 полоски: FN_SET_ACC_BARS(3, 4)
            MOVN        A, #4
            PUSHW       A
            MOVN        A, #3           ; LEVEL = 3
            PUSHW       A
            CALLP       [FN_SET_ACC_BARS]
            ADD         SSP, #0x04
            BRA         .exit

.stage_strobe:
            ; Инвертируем байт полупериода мигания для стробоскопа
            MOV         A, [RAM_BLINK_STATE]
            XOR         A, #0x01
            MOV         [RAM_BLINK_STATE], A
            CMP         A, #0x01
            BNE         .acc_all_off    ; В фазе "выкл" гасим всё

            ; В фазе "вкл" зажигаем боковые рельсы и все 4 полоски!
            MOVN        A, #1
            PUSHW       A
            MOV         A, #ID_ACC_ROAD
            PUSHW       A
            CALLP       [FN_SET_TELLTALE]
            ADD         SSP, #0x04

            MOVN        A, #4
            PUSHW       A
            MOVN        A, #4           ; LEVEL = 4 (все полоски)
            PUSHW       A
            CALLP       [FN_SET_ACC_BARS]
            ADD         SSP, #0x04
            BRA         .exit

.acc_all_off:
            ; Выключаем боковые рельсы
            MOVN        A, #0
            PUSHW       A
            MOV         A, #ID_ACC_ROAD
            PUSHW       A
            CALLP       [FN_SET_TELLTALE]
            ADD         SSP, #0x04

            ; Выключаем все полоски: FN_SET_ACC_BARS(0, 4)
            MOVN        A, #4
            PUSHW       A
            MOVN        A, #0           ; LEVEL = 0
            PUSHW       A
            CALLP       [FN_SET_ACC_BARS]
            ADD         SSP, #0x04

.exit:
            POPW        RLST(0xC7)
            UNLINK
            RETP
