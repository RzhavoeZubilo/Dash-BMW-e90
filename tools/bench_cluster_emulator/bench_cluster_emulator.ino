// ==============================================================================
//  BMW E90 Instrument Cluster (KOMBI) Bench Emulator
//  Эмулятор стенда для приборной панели BMW E90 (K-CAN 100 kbps)
// ==============================================================================
//  Позволяет включить приборную панель на столе без автомобиля:
//  - Кадр зажигания 0x130 (пробуждение и удержание Kl.15)
//  - Обороты двигателя 0x0AA (тахометр)
//  - Скорость 0x1A6 (спидометр)
//  - Режим селектора АКПП 0x1D2 (P, R, N, D, M1..M8)
//  - Индикация ACC 0x190/0x193 (машинка и 4 полоски дистанции для Shift-Light)
//
//  Управление через Serial Monitor (115200 бод):
//    w / s - увеличить / уменьшить обороты (+/- 500 RPM)
//    p, r, n, d, m - переключение режима коробки
//    1 .. 8 - выбор передачи в режиме M
//    a - переключение полосок ACC (0 -> 1 -> 2 -> 3 -> 4 -> стробоскоп)
//    t - авто-тест (sweep оборотов 0..7000 RPM для проверки шифтлайта)
// ==============================================================================

#include <SPI.h>
#include <mcp_can.h>

// ------------------------------------------------------------------------------
// Настройки оборудования
// ------------------------------------------------------------------------------
#define CAN_CS_PIN    10     // Пин CS модуля MCP2515 (на Nano обычно D10)
#define CAN_OSC_8MHZ  1      // 1 если на плате кварц 8 МГц, 0 если 16 МГц

#if CAN_OSC_8MHZ
  #define MCP_CLOCK_SETTING MCP_8MHZ
#else
  #define MCP_CLOCK_SETTING MCP_16MHZ
#endif

MCP_CAN CAN(CAN_CS_PIN);

// ------------------------------------------------------------------------------
// Переменные состояния стенда
// ------------------------------------------------------------------------------
bool sweepMode = false;
int  targetRpm = 0;
int  speedKmh  = 0;

// Режимы коробки:
// 0=P, 1=R, 2=N, 3=D, 4=M
uint8_t gearMode = 3;  // По умолчанию 'D'
uint8_t currentGear = 1; // Передача 1..8

// Ступени полосок ACC:
// 0=выкл, 1=1 полоска, 2=2 полоски, 3=3 полоски, 4=все 4, 5=стробоскоп
uint8_t accBars = 0;
bool accBlinkState = false;

// Таймеры отправки кадров
unsigned long last100ms = 0;
unsigned long last200ms = 0;
unsigned long lastSweep = 0;
uint8_t aliveCounterAA  = 0;

// ------------------------------------------------------------------------------
// Вспомогательные функции отправки CAN
// ------------------------------------------------------------------------------

// 0x130: Car Access System (CAS) - статус зажигания и ключа
void sendIgnitionStatus() {
    // Byte 0: 0x45 (Kl.15 ON, двигатель запущен), Byte 1: 0x40 (ключ в замке)
    unsigned char frame[8] = { 0x45, 0x40, 0x20, 0x8F, 0xFE, 0x00, 0x00, 0x00 };
    CAN.sendMsgBuf(0x130, 0, 8, frame);
}

// 0x0AA: Обороты двигателя (DME)
void sendEngineRpm(int rpm) {
    if (rpm < 0) rpm = 0;
    if (rpm > 8000) rpm = 8000;
    uint16_t rawRpm = (uint16_t)(rpm * 4); // множитель 0.25 об/мин

    aliveCounterAA = (aliveCounterAA + 1) & 0x0E;

    unsigned char frame[8] = { 0 };
    frame[0] = 0xFE; // Dummy CRC/статус
    frame[1] = aliveCounterAA | 0x01;
    frame[2] = 0x00;
    frame[3] = 0x00;
    frame[4] = rawRpm & 0xFF;
    frame[5] = (rawRpm >> 8) & 0xFF;
    frame[6] = 0x00;
    frame[7] = 0x00;

    CAN.sendMsgBuf(0x0AA, 0, 8, frame);
}

// 0x1A6: Скорость автомобиля (DSC)
void sendVehicleSpeed(int kmh) {
    if (kmh < 0) kmh = 0;
    uint16_t rawSpeed = (uint16_t)(kmh * 10);

    unsigned char frame[8] = { 0 };
    frame[0] = rawSpeed & 0xFF;
    frame[1] = (rawSpeed >> 8) & 0x0F;
    frame[2] = rawSpeed & 0xFF;
    frame[3] = (rawSpeed >> 8) & 0x0F;
    frame[4] = 0x00;
    frame[5] = 0x00;
    frame[6] = 0x00;
    frame[7] = 0x00;

    CAN.sendMsgBuf(0x1A6, 0, 8, frame);
}

// 0x1D2: Селектор АКПП и номер передачи
void sendGearSelection(uint8_t mode, uint8_t gear) {
    unsigned char frame[5] = { 0 };

    // Байт 0: режим отображения
    // 0x0B = P, 0x0D = R, 0x0E = N, 0x07 = D, 0x5C = M/S
    switch (mode) {
        case 0: frame[0] = 0x0B; break; // P
        case 1: frame[0] = 0x0D; break; // R
        case 2: frame[0] = 0x0E; break; // N
        case 3: frame[0] = 0x07; break; // D
        case 4: frame[0] = 0x5C; break; // M
        default: frame[0] = 0x07; break;
    }

    // Байт 1: младшие биты - номер передачи (1..8)
    if (mode == 4) { // Manual
        frame[1] = (gear & 0x0F);
    } else {
        frame[1] = 0x00;
    }

    frame[2] = 0x00;
    frame[3] = 0x00;
    frame[4] = 0x00;

    CAN.sendMsgBuf(0x1D2, 0, 5, frame);
}

// 0x190: Индикация ACC (полоски и силуэт машины)
void sendAccStatus(uint8_t bars, bool blink) {
    unsigned char frame[8] = { 0 };

    // Если включен стробоскоп и полупериод выключен
    if (bars == 5 && !blink) {
        CAN.sendMsgBuf(0x190, 0, 8, frame);
        return;
    }

    uint8_t stage = (bars == 5) ? 4 : bars;

    // Байт 0: биты отображения полосок (1..4)
    // Байт 1: флаг силуэта машины
    if (stage > 0) {
        frame[0] = 0x08 | (stage & 0x07); // Статус полосок
        frame[1] = 0x40;                  // Флаг активной машинки ACC
        frame[2] = (stage * 25);          // Дистанция
    }

    CAN.sendMsgBuf(0x190, 0, 8, frame);
}

// ------------------------------------------------------------------------------
// Setup
// ------------------------------------------------------------------------------
void setup() {
    Serial.begin(115200);
    while (!Serial) { delay(10); }

    Serial.println(F("\n========================================"));
    Serial.println(F(" BMW E90 KOMBI Bench Simulator"));
    Serial.println(F("========================================"));

    // Инициализация MCP2515 на скорости 100 кбит/с (K-CAN)
    if (CAN.begin(MCP_ANY, CAN_100KBPS, MCP_CLOCK_SETTING) == CAN_OK) {
        Serial.println(F("[OK] CAN контроллер инициализирован (100 kbps)"));
    } else {
        Serial.println(F("[ОШИБКА] Не удалось инициализировать MCP2515!"));
        Serial.println(F("Проверьте SPI подключение и кварц (8 или 16 МГц)."));
        while (1) { delay(500); }
    }

    CAN.setMode(MCP_NORMAL);

    Serial.println(F("\nКоманды управления:"));
    Serial.println(F("  w / s  - Обороты тахометра (+/- 500 RPM)"));
    Serial.println(F("  p/r/n/d/m - Селектор АКПП (P, R, N, D, M)"));
    Serial.println(F("  1 .. 8 - Выбор передачи в режиме M"));
    Serial.println(F("  a      - Тест полосок ACC (0..4 и стробоскоп)"));
    Serial.println(F("  t      - Автоматический Sweep оборотов 0..7000"));
    Serial.println(F("----------------------------------------\n"));
}

// ------------------------------------------------------------------------------
// Главный цикл
// ------------------------------------------------------------------------------
void loop() {
    unsigned long now = millis();

    // 1. Обработка команд из Serial Monitor
    if (Serial.available()) {
        char c = (char)Serial.read();
        switch (c) {
            case 'w': case 'W':
                sweepMode = false;
                targetRpm = min(targetRpm + 500, 7500);
                speedKmh = targetRpm / 50;
                Serial.print(F("RPM: ")); Serial.println(targetRpm);
                break;
            case 's': case 'S':
                sweepMode = false;
                targetRpm = max(targetRpm - 500, 0);
                speedKmh = targetRpm / 50;
                Serial.print(F("RPM: ")); Serial.println(targetRpm);
                break;
            case 'p': case 'P': gearMode = 0; Serial.println(F("Режим: [P]")); break;
            case 'r': case 'R': gearMode = 1; Serial.println(F("Режим: [R]")); break;
            case 'n': case 'N': gearMode = 2; Serial.println(F("Режим: [N]")); break;
            case 'd': case 'D': gearMode = 3; Serial.println(F("Режим: [D]")); break;
            case 'm': case 'M': gearMode = 4; Serial.println(F("Режим: [M]")); break;
            case '1': case '2': case '3': case '4':
            case '5': case '6': case '7': case '8':
                gearMode = 4; // Переключаем в Manual
                currentGear = c - '0';
                Serial.print(F("Передача: M")); Serial.println(currentGear);
                break;
            case 'a': case 'A':
                accBars = (accBars + 1) % 6;
                Serial.print(F("ACC ступень: ")); Serial.println(accBars);
                break;
            case 't': case 'T':
                sweepMode = !sweepMode;
                Serial.print(F("Авто-Sweep: ")); Serial.println(sweepMode ? F("ВКЛ") : F("ВЫКЛ"));
                break;
        }
    }

    // 2. Логика авто-sweep для демонстрации шифтлайта
    if (sweepMode && (now - lastSweep >= 50)) {
        lastSweep = now;
        static int sweepDir = 100;
        targetRpm += sweepDir;
        if (targetRpm >= 7000) { sweepDir = -150; }
        if (targetRpm <= 800)  { sweepDir = 100; }
        speedKmh = targetRpm / 50;

        // Автоматический шифтлайт по оборотам:
        if (targetRpm >= 6200)      accBars = 5; // стробоскоп
        else if (targetRpm >= 6000) accBars = 3;
        else if (targetRpm >= 5500) accBars = 2;
        else if (targetRpm >= 5000) accBars = 1;
        else                        accBars = 0;
    }

    // 3. Отправка быстрых кадров (каждые 100 мс)
    if (now - last100ms >= 100) {
        last100ms = now;
        sendIgnitionStatus();
        sendEngineRpm(targetRpm);
        sendVehicleSpeed(speedKmh);
        sendGearSelection(gearMode, currentGear);
    }

    // 4. Отправка медленных кадров (каждые 200 мс) и мигание стробоскопа
    if (now - last200ms >= 200) {
        last200ms = now;
        accBlinkState = !accBlinkState;
        sendAccStatus(accBars, accBlinkState);
    }
}
