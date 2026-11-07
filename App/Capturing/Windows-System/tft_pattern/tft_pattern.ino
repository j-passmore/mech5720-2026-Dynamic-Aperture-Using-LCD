 /*
 * tft_pattern.ino
 * ---------------------------------------------------------------------------
 * Receives 1-bit (pure black / white) images over USB serial from the laptop
 * (see ../send_pattern.py) and draws them pixel-exact on an Adafruit 1.8"
 * ST7735 TFT (128x160, product #358 breakout).
 *
 * Board: inventr.io HERO (Arduino Uno compatible, ATmega328P, 5 V logic).
 *        In the Arduino IDE select  Tools > Board > "Arduino Uno".
 *
 * Libraries (Arduino IDE > Library Manager):
 *   - "Adafruit ST7735 and ST7789 Library"
 *   - "Adafruit GFX Library"   (installed automatically as a dependency)
 *
 * ===========================================================================
 *  WIRING:  Adafruit 1.8" TFT breakout (#358)  ->  HERO board
 * ===========================================================================
 *  The #358 breakout has its own 3.3 V regulator and level shifter, so it is
 *  safe to drive straight from the HERO's 5 V pins. (If you have a generic,
 *  non-Adafruit ST7735 module, check it is 5 V tolerant first!)
 *
 *  Pin labels differ slightly between board revisions; both are listed.
 *
 *   TFT pin            HERO pin    Notes
 *   -----------------  ----------  -----------------------------------------
 *   VCC / Vin          5V          Power
 *   GND                GND         Ground
 *   SCK / SCLK         D13         Hardware SPI clock     (fixed on Uno)
 *   MOSI / SI          D11         Hardware SPI data out  (fixed on Uno)
 *   TFT_CS / TCS       D10         TFT chip select        (TFT_CS below)
 *   D/C / DC           D8          Data/command select    (TFT_DC below)
 *   RESET / RST        D9          Display reset          (TFT_RST below)
 *   LITE / Lite        5V          Backlight always on (or a PWM pin such as
 *                                  D6 + analogWrite() for adjustable brightness)
 *   MISO / SO          (unused)    Only needed for the microSD card -> D12
 *   CARD_CS / CCS      (unused)    Only needed for the microSD card -> D4
 *
 *  D11 and D13 are fixed by the ATmega328P's hardware SPI. CS/DC/RST can be
 *  moved to any digital pin if you update the #defines below.
 * ===========================================================================
 *
 * Serial protocol (115200 baud, 8N1):
 *   Laptop -> '?'      Arduino -> "READY <width> <height>\n"
 *   Laptop -> 'I'      Arduino -> 'R' before each row; laptop replies with one
 *                      row of width/8 bytes (MSB = leftmost pixel, 1 = white).
 *                      After the last row: "DONE\n" (or "ERR ...\n").
 *   Rows are drawn as they arrive, so the 2 KB of RAM never has to hold the
 *   whole frame. The per-row 'R' handshake stops the 64-byte serial receive
 *   buffer from overflowing.
 */

#include <Adafruit_GFX.h>
#include <Adafruit_ST7735.h>
#include <SPI.h>

// ---- Pin assignment (see wiring table above) ------------------------------
#define TFT_CS   10
#define TFT_DC    8
#define TFT_RST   9

// ---- Display configuration -------------------------------------------------
// 0 = portrait 128x160, 1 = landscape 160x128 (2/3 = the same, flipped 180 deg)
#define ROTATION  1

// The ST7735 panels ship with different coloured tabs on the screen protector.
// If you see a stripe of random pixels along one edge, or the image looks
// shifted, try INITR_GREENTAB or INITR_REDTAB instead.
#define TFT_TAB   INITR_BLACKTAB

#define BAUD           115200
#define ROW_TIMEOUT_MS 1000
#define MAX_ROW_BYTES  (160 / 8)   // widest orientation

Adafruit_ST7735 tft = Adafruit_ST7735(TFT_CS, TFT_DC, TFT_RST);

uint8_t rowBuf[MAX_ROW_BYTES];

void printReady() {
  Serial.print(F("READY "));
  Serial.print(tft.width());
  Serial.print(' ');
  Serial.println(tft.height());
}

// Draw one row of packed 1-bit pixels into the already-open address window.
// Same-coloured runs go out with a single writeColor() call, which is quick
// for stripe / Gray-code patterns.
void drawRow(const uint8_t *row, uint16_t w) {
  bool cur = row[0] & 0x80;
  uint16_t run = 0;
  for (uint16_t x = 0; x < w; x++) {
    bool px = (row[x >> 3] >> (7 - (x & 7))) & 1;
    if (px == cur) {
      run++;
    } else {
      tft.writeColor(cur ? ST77XX_WHITE : ST77XX_BLACK, run);
      cur = px;
      run = 1;
    }
  }
  tft.writeColor(cur ? ST77XX_WHITE : ST77XX_BLACK, run);
}

void receiveImage() {
  const uint16_t w = tft.width();
  const uint16_t h = tft.height();
  const uint8_t rowBytes = w / 8;

  tft.startWrite();
  tft.setAddrWindow(0, 0, w, h);   // pixels then stream left->right, top->bottom

  for (uint16_t y = 0; y < h; y++) {
    Serial.write('R');
    if (Serial.readBytes(rowBuf, rowBytes) != rowBytes) {
      tft.endWrite();
      Serial.print(F("ERR timeout at row "));
      Serial.println(y);
      return;
    }
    drawRow(rowBuf, w);
  }

  tft.endWrite();
  Serial.println(F("DONE"));
}

void setup() {
  Serial.begin(BAUD);
  Serial.setTimeout(ROW_TIMEOUT_MS);

  tft.initR(TFT_TAB);
  tft.setRotation(ROTATION);
  tft.fillScreen(ST77XX_BLACK);

  printReady();
}

void loop() {
  if (!Serial.available()) return;

  char cmd = Serial.read();
  if (cmd == '?') {
    printReady();
  } else if (cmd == 'I') {
    receiveImage();
  }
  // Anything else (stray newlines etc.) is ignored.
}
