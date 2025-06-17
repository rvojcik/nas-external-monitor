#include <M5GFX.h>

M5GFX display;

// M5Stack Core speaker pin
#define SPEAKER_PIN 25

// Modern color scheme
#define BLACK     0x0000
#define DARK_GREY 0x18C3
#define GREY      0x7BEF
#define LIGHT_GREY 0xC618
#define WHITE     0xFFFF
#define BLUE      0x1B5F    // Modern blue
#define DARK_BLUE 0x0A3F    // Header background
#define GREEN     0x07E8    // Success green
#define ORANGE    0xFD20    // Warning orange  
#define RED       0xF800    // Error red
#define RED_DARK  0xA000    // Dark red for bars
#define YELLOW    0xFFE0

int _width = 320;
int _height = 240;

struct SystemData {
  float systemTemp;
  float hdd1Temp;
  float hdd2Temp;
  float hdd3Temp;
  float hdd4Temp;
  float hdd5Temp;
  String storageState;
  unsigned long lastUpdate;
  bool hasError;
};

SystemData sysData = {0, 0, 0, 0, 0, 0, "Unknown", 0, false};
SystemData lastDisplayData = {-1, -1, -1, -1, -1, -1, "", 0, false}; // Track last displayed values
const unsigned long UPDATE_TIMEOUT = 60000;
const float TEMP_THRESHOLD = 52.0;
bool forceRedraw = true;
bool lastHighTempState = false;
bool lastStorageProblemState = false;

void initDisplay() {
  display.begin();
  display.setRotation(1); // Landscape orientation
  display.fillScreen(BLACK);
  display.setTextColor(WHITE);
  display.setFont(&fonts::Font2); // Use built-in font
}

void fillScreen(uint16_t color) {
  display.fillScreen(color);
}

void fillRect(int x, int y, int w, int h, uint16_t color) {
  display.fillRect(x, y, w, h, color);
}


void drawString(int x, int y, String str, uint16_t color) {
  display.setCursor(x, y);
  display.setTextColor(color);
  display.setTextSize(1);
  display.print(str);
}

void drawStringLarge(int x, int y, String str, uint16_t color) {
  display.setCursor(x, y);
  display.setTextColor(color);
  display.setTextSize(2);
  display.print(str);
}

void drawStringMedium(int x, int y, String str, uint16_t color) {
  display.setCursor(x, y);
  display.setTextColor(color);
  display.setTextSize(1);
  display.setFont(&fonts::Font4); // Slightly larger than default
  display.print(str);
  display.setFont(&fonts::Font2); // Reset to default
}

void beep(int frequency, int duration) {
  tone(SPEAKER_PIN, frequency, duration);
  delay(duration);
  noTone(SPEAKER_PIN);
}

void alertBeep() {
  // Triple beep pattern for alerts
  beep(1000, 200);
  delay(100);
  beep(1000, 200);
  delay(100);
  beep(1000, 200);
}

void setup() {
  Serial.begin(115200);
  delay(2000);
  
  Serial.println("=== M5Stack System Monitor Starting ===");
  Serial.println("Initializing display...");
  
  // Initialize speaker
  pinMode(SPEAKER_PIN, OUTPUT);
  
  initDisplay();
  fillScreen(BLACK);
  
  Serial.println("Drawing interface...");
  drawHeader();
  displaySystemInfo();
  
  sysData.lastUpdate = millis();
  Serial.println("System ready!");
  Serial.println("Waiting for UPDATE commands...");
  Serial.println("Format: UPDATE:sys_temp,hdd1,hdd2,hdd3,hdd4,hdd5,storage_state");
  Serial.println("Example: UPDATE:45.2,38.1,42.5,39.8,41.2,43.6,Healthy");
}

void loop() {
  checkSerialData();
  
  static bool errorReported = false;
  bool previousErrorState = sysData.hasError;
  
  if (millis() - sysData.lastUpdate > UPDATE_TIMEOUT) {
    if (!sysData.hasError) {
      Serial.println("WARNING: 60 second timeout exceeded! Setting error state.");
      errorReported = false;
      forceRedraw = true;
    }
    sysData.hasError = true;
    if (!errorReported) {
      Serial.println("ERROR: No updates received for more than 1 minute!");
      errorReported = true;
    }
  } else {
    if (sysData.hasError) {
      Serial.println("INFO: Error state cleared - updates resumed");
      errorReported = false;
      forceRedraw = true;
    }
    sysData.hasError = false;
  }
  
  displaySystemInfo();
  
  delay(5000);
}

void drawHeader() {
  // Modern gradient-like header - optimized size
  fillRect(0, 0, 320, 28, DARK_BLUE);
  fillRect(0, 28, 320, 2, BLUE);
  
  // Title with medium font (20% smaller than large)
  drawStringMedium(10, 6, "NAS MONITOR", WHITE);
  
  // Status indicator dot
  fillRect(280, 8, 8, 8, GREEN);
  
  Serial.println("M5GFX header with medium-sized title");
}

bool needsRedraw() {
  return forceRedraw || 
         sysData.systemTemp != lastDisplayData.systemTemp ||
         sysData.hdd1Temp != lastDisplayData.hdd1Temp ||
         sysData.hdd2Temp != lastDisplayData.hdd2Temp ||
         sysData.hdd3Temp != lastDisplayData.hdd3Temp ||
         sysData.hdd4Temp != lastDisplayData.hdd4Temp ||
         sysData.hdd5Temp != lastDisplayData.hdd5Temp ||
         sysData.storageState != lastDisplayData.storageState ||
         sysData.hasError != lastDisplayData.hasError;
}

void drawTempRow(int y, String label, float temp, uint16_t bgColor) {
  // Clear row background - bigger rows to fill display
  fillRect(0, y, 320, 26, bgColor);
  
  // Text color based on background
  uint16_t textColor = (bgColor == RED) ? BLACK : WHITE;
  uint16_t labelColor = (bgColor == RED) ? BLACK : LIGHT_GREY;
  
  // Label - bigger text with better positioning
  drawStringMedium(10, y + 6, label, labelColor);
  
  // Temperature bar background - adjusted to not overlap with values
  fillRect(120, y + 5, 120, 16, DARK_GREY);
  
  // Temperature bar fill
  int barWidth = (int)(temp * 2.6); // Adjusted scaling for shorter bar
  if (barWidth > 120) barWidth = 120;
  if (barWidth < 0) barWidth = 0;
  
  uint16_t barColor;
  if (temp > TEMP_THRESHOLD) {
    barColor = (bgColor == RED) ? RED_DARK : RED;
  } else if (temp > TEMP_THRESHOLD - 5) {
    barColor = ORANGE;
  } else {
    barColor = GREEN;
  }
  
  if (barWidth > 0) {
    fillRect(120, y + 5, barWidth, 16, barColor);
  }
  
  // Temperature value - positioned after the bar
  char tempBuffer[10];
  dtostrf(temp, 4, 1, tempBuffer);
  String tempStr = String(tempBuffer) + " C";
  tempStr.replace(',', '.');
  drawStringMedium(245, y + 6, tempStr, textColor);
}

void displaySystemInfo() {
  if (!needsRedraw()) {
    return;
  }
  
  uint16_t bgColor = BLACK;
  bool highTemp = (sysData.systemTemp > TEMP_THRESHOLD || 
                   sysData.hdd1Temp > TEMP_THRESHOLD || 
                   sysData.hdd2Temp > TEMP_THRESHOLD || 
                   sysData.hdd3Temp > TEMP_THRESHOLD || 
                   sysData.hdd4Temp > TEMP_THRESHOLD || 
                   sysData.hdd5Temp > TEMP_THRESHOLD);
  bool storageProb = (sysData.storageState == "Problem");
  
  if (sysData.hasError) {
    bgColor = RED;
    Serial.println("Display: RED background (Error state)");
  } else if (highTemp || storageProb) {
    bgColor = RED;
    if (highTemp && storageProb) {
      Serial.println("Display: RED background (High temperature + Storage problem)");
    } else if (highTemp) {
      Serial.println("Display: RED background (High temperature)");
    } else {
      Serial.println("Display: RED background (Storage problem)");
    }
  } else {
    bgColor = DARK_GREY;
    Serial.println("Display: DARK_GREY background (Normal)");
  }
  
  // Check for new alert conditions and beep
  if (highTemp && !lastHighTempState) {
    Serial.println("ALERT: High temperature detected - beeping");
    alertBeep();
  }
  
  if (storageProb && !lastStorageProblemState) {
    Serial.println("ALERT: Storage problem detected - beeping");
    alertBeep();
  }
  
  // Update previous states
  lastHighTempState = highTemp;
  lastStorageProblemState = storageProb;
  
  // Clear main area - optimized for smaller header
  fillRect(0, 30, 320, 210, bgColor);
  
  // Expanded layout to fill display completely
  int yPos = 34;
  int rowHeight = 26; // Bigger rows
  
  // Temperature readings with labels - all bigger
  drawTempRow(yPos, "SYSTEM:", sysData.systemTemp, bgColor);
  yPos += rowHeight;
  
  drawTempRow(yPos, "HDD1:", sysData.hdd1Temp, bgColor);
  yPos += rowHeight;
  
  drawTempRow(yPos, "HDD2:", sysData.hdd2Temp, bgColor);
  yPos += rowHeight;
  
  drawTempRow(yPos, "HDD3:", sysData.hdd3Temp, bgColor);
  yPos += rowHeight;
  
  drawTempRow(yPos, "HDD4:", sysData.hdd4Temp, bgColor);
  yPos += rowHeight;
  
  drawTempRow(yPos, "HDD5:", sysData.hdd5Temp, bgColor);
  yPos += rowHeight + 4;
  
  // Storage status - bigger to fill remaining space
  fillRect(0, yPos, 320, 28, bgColor);
  
  // Text color based on background
  uint16_t textColor = (bgColor == RED) ? BLACK : WHITE;
  uint16_t labelColor = (bgColor == RED) ? BLACK : LIGHT_GREY;
  
  drawStringMedium(10, yPos + 8, "STORAGE:", labelColor);
  
  // Storage status text without background bar - just colored text
  uint16_t statusColor = (sysData.storageState == "Healthy") ? GREEN : WHITE;
  String statusText = (sysData.storageState == "Healthy") ? "HEALTHY" : "PROBLEM";
  
  drawStringMedium(140, yPos + 8, statusText, statusColor);
  yPos += 32;
  
  // Error message - fills bottom space completely
  if (sysData.hasError) {
    fillRect(5, yPos, 310, 22, RED);
    drawString(10, 225, "NO DATA UPDATE", WHITE);
  }
  
  // Update header status indicator
  fillRect(280, 8, 8, 8, sysData.hasError ? RED : (bgColor == RED ? ORANGE : GREEN));
  
  lastDisplayData = sysData;
  forceRedraw = false;
  
  Serial.println("Modern display updated with labeled temperature readings");
}

void checkSerialData() {
  if (Serial.available()) {
    String command = Serial.readStringUntil('\n');
    command.trim();
    
    Serial.print("Received: ");
    Serial.println(command);
    
    if (command.startsWith("UPDATE:")) {
      Serial.println("Processing UPDATE command...");
      parseUpdate(command);
      sysData.lastUpdate = millis();
      sysData.hasError = false;
      forceRedraw = true; // Trigger display update
      Serial.println("Update processed successfully!");
      Serial.printf("System: %.1f°C, HDD1: %.1f°C, HDD2: %.1f°C, HDD3: %.1f°C, HDD4: %.1f°C, HDD5: %.1f°C, Storage: %s\n",
                    sysData.systemTemp, sysData.hdd1Temp, sysData.hdd2Temp, 
                    sysData.hdd3Temp, sysData.hdd4Temp, sysData.hdd5Temp, 
                    sysData.storageState.c_str());
    } else {
      Serial.println("Unknown command - expecting UPDATE:...");
    }
  }
}

void parseUpdate(String command) {
  command.replace("UPDATE:", "");
  
  int commaIndex = 0;
  int lastIndex = 0;
  int fieldIndex = 0;
  
  while (commaIndex != -1 && fieldIndex < 7) {
    commaIndex = command.indexOf(',', lastIndex);
    String value;
    
    if (commaIndex != -1) {
      value = command.substring(lastIndex, commaIndex);
    } else {
      value = command.substring(lastIndex);
    }
    
    value.trim();
    
    switch (fieldIndex) {
      case 0: sysData.systemTemp = value.toFloat(); break;
      case 1: sysData.hdd1Temp = value.toFloat(); break;
      case 2: sysData.hdd2Temp = value.toFloat(); break;
      case 3: sysData.hdd3Temp = value.toFloat(); break;
      case 4: sysData.hdd4Temp = value.toFloat(); break;
      case 5: sysData.hdd5Temp = value.toFloat(); break;
      case 6: sysData.storageState = value; break;
    }
    
    lastIndex = commaIndex + 1;
    fieldIndex++;
  }
}