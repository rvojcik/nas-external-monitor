#include <M5GFX.h>

M5GFX display;

// M5Stack Core pins
#define SPEAKER_PIN 25
#define BUTTON_A_PIN 39  // Button 1 (Back)
#define BUTTON_B_PIN 38  // Button 2 (Middle) 
#define BUTTON_C_PIN 37  // Button 3 (Next)

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

// Screen definitions
enum Screen {
  SCREEN_MAIN = 0,
  SCREEN_NETWORK = 1,
  SCREEN_STORAGE = 2,
  SCREEN_COUNT = 3
};

struct PoolData {
  String name;
  String capacity;
  String usage;
  String state;
};

struct SystemData {
  float systemTemp;
  float hdd1Temp;
  float hdd2Temp;
  float hdd3Temp;
  float hdd4Temp;
  float hdd5Temp;
  String storageState;
  String macAddress;
  String ipv4Address;
  String ipv6Address;
  PoolData pools[4]; // Support up to 4 storage pools
  int poolCount;
  unsigned long lastUpdate;
  bool hasError;
};

SystemData sysData = {0, 0, 0, 0, 0, 0, "Unknown", "", "", "", {}, 0, 0, false};
SystemData lastDisplayData = {-1, -1, -1, -1, -1, -1, "", "", "", "", {}, 0, 0, false};
const unsigned long UPDATE_TIMEOUT = 60000;
const float TEMP_THRESHOLD = 52.0;
bool forceRedraw = true;
bool lastHighTempState = false;
bool lastStorageProblemState = false;

// Navigation variables
Screen currentScreen = SCREEN_MAIN;
Screen lastScreen = SCREEN_MAIN;
bool buttonAPressed = false;
bool buttonCPressed = false;
unsigned long lastButtonPress = 0;
const unsigned long BUTTON_DEBOUNCE = 200;

void initDisplay() {
  display.begin();
  display.setRotation(1); // Landscape orientation
  display.fillScreen(BLACK);
  display.setTextColor(WHITE);
  display.setFont(&fonts::Font2); // Use built-in font
  
  // Initialize buttons
  pinMode(BUTTON_A_PIN, INPUT_PULLUP);
  pinMode(BUTTON_B_PIN, INPUT_PULLUP);
  pinMode(BUTTON_C_PIN, INPUT_PULLUP);
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
  //beep(1000, 200);
  //delay(100);
  //beep(1000, 200);
  //delay(100);
  //beep(1000, 200);
}

void handleButtons() {
  unsigned long currentTime = millis();
  
  // Debounce protection
  if (currentTime - lastButtonPress < BUTTON_DEBOUNCE) {
    return;
  }
  
  // Button A (Back) - Previous screen
  if (digitalRead(BUTTON_A_PIN) == LOW && !buttonAPressed) {
    buttonAPressed = true;
    lastButtonPress = currentTime;
    currentScreen = (Screen)((currentScreen - 1 + SCREEN_COUNT) % SCREEN_COUNT);
    forceRedraw = true;
    Serial.println("Button A pressed - Previous screen");
  } else if (digitalRead(BUTTON_A_PIN) == HIGH) {
    buttonAPressed = false;
  }
  
  // Button C (Next) - Next screen
  if (digitalRead(BUTTON_C_PIN) == LOW && !buttonCPressed) {
    buttonCPressed = true;
    lastButtonPress = currentTime;
    currentScreen = (Screen)((currentScreen + 1) % SCREEN_COUNT);
    forceRedraw = true;
    Serial.println("Button C pressed - Next screen");
  } else if (digitalRead(BUTTON_C_PIN) == HIGH) {
    buttonCPressed = false;
  }
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
  displayCurrentScreen();
  
  sysData.lastUpdate = millis();
  Serial.println("System ready with multi-screen navigation!");
  Serial.println("Button 1 (A): Previous screen | Button 3 (C): Next screen");
  Serial.println("");
  Serial.println("=== SERIAL COMMANDS ===");
  Serial.println("1. Temperature data:");
  Serial.println("   UPDATE:sys_temp,hdd1,hdd2,hdd3,hdd4,hdd5,storage_state");
  Serial.println("   Example: UPDATE:45.2,38.1,42.5,39.8,41.2,43.6,Healthy");
  Serial.println("");
  Serial.println("2. Network information:");
  Serial.println("   NETWORK:mac_address,ipv4_address,ipv6_address");
  Serial.println("   Example: NETWORK:aa:bb:cc:dd:ee:ff,192.168.1.100,2001:db8::1");
  Serial.println("");
  Serial.println("3. Storage pools:");
  Serial.println("   POOL:RESET (clears all pools)");
  Serial.println("   POOL:name,capacity,usage,state");
  Serial.println("   Example: POOL:tank1,2TB,65%,Healthy");
  Serial.println("            POOL:backup,1TB,80%,Degraded");
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
  
  handleButtons();
  displayCurrentScreen();
  
  delay(100); // Reduced for better button responsiveness
}

void drawHeader() {
  // Modern gradient-like header - optimized size
  fillRect(0, 0, 320, 28, DARK_BLUE);
  fillRect(0, 28, 320, 2, BLUE);
  
  // Title with screen indicator
  String headerTitle = "NAS MONITOR";
  switch(currentScreen) {
    case SCREEN_MAIN:
      break;
    case SCREEN_NETWORK:
      headerTitle = "Network";
      break;
    case SCREEN_STORAGE:
      headerTitle = "Storage detail";
      break;
  }
  
  drawStringMedium(10, 6, headerTitle, WHITE);
  
  // Status indicator dot
  fillRect(280, 8, 8, 8, GREEN);
  
  // Navigation indicators
  drawString(5, 6, "<", WHITE);   // Back button
  drawString(305, 6, ">", WHITE); // Next button
  
  Serial.println("M5GFX header with screen: " + String(currentScreen));
}

bool needsRedraw() {
  return forceRedraw || 
         currentScreen != lastScreen ||
         sysData.systemTemp != lastDisplayData.systemTemp ||
         sysData.hdd1Temp != lastDisplayData.hdd1Temp ||
         sysData.hdd2Temp != lastDisplayData.hdd2Temp ||
         sysData.hdd3Temp != lastDisplayData.hdd3Temp ||
         sysData.hdd4Temp != lastDisplayData.hdd4Temp ||
         sysData.hdd5Temp != lastDisplayData.hdd5Temp ||
         sysData.storageState != lastDisplayData.storageState ||
         sysData.macAddress != lastDisplayData.macAddress ||
         sysData.ipv4Address != lastDisplayData.ipv4Address ||
         sysData.ipv6Address != lastDisplayData.ipv6Address ||
         sysData.poolCount != lastDisplayData.poolCount ||
         sysData.hasError != lastDisplayData.hasError;
}

void displayNetworkScreen() {
  // Clear main area
  fillRect(0, 30, 320, 210, BLACK);
  
  int yPos = 40;
  int rowHeight = 45;
  
  // MAC Address
  drawStringMedium(10, yPos, "MAC ADDRESS:", LIGHT_GREY);
  drawStringMedium(10, yPos + 25, sysData.macAddress, WHITE);
  yPos += rowHeight + 10;
  
  // IPv4 Address
  drawStringMedium(10, yPos, "IPv4 ADDRESS:", LIGHT_GREY);
  drawStringMedium(10, yPos + 25, sysData.ipv4Address, GREEN);
  yPos += rowHeight + 10;
  
  // IPv6 Address
  drawStringMedium(10, yPos, "IPv6 ADDRESS:", LIGHT_GREY);
  // Split long IPv6 address if needed
  String ipv6 = sysData.ipv6Address;
  if (ipv6.length() > 25) {
    String line1 = ipv6.substring(0, 25);
    String line2 = ipv6.substring(25);
    drawStringMedium(10, yPos + 25, line1, BLUE);
    drawStringMedium(10, yPos + 40, line2, BLUE);
  } else {
    drawStringMedium(10, yPos + 25, ipv6, BLUE);
  }
  
  // Navigation hint
  drawString(10, 220, "Button 1: Back  |  Button 3: Next", GREY);
}

void displayStorageScreen() {
  // Clear main area
  fillRect(0, 30, 320, 210, BLACK);
  
  int yPos = 40;
   
  // Draw table header
  fillRect(5, yPos, 310, 2, GREY);
  yPos += 5;
  
  drawString(10, yPos, "NAME", LIGHT_GREY);
  drawString(80, yPos, "CAPACITY", LIGHT_GREY);
  drawString(160, yPos, "USED", LIGHT_GREY);
  drawString(220, yPos, "STATE", LIGHT_GREY);
  yPos += 15;
  
  fillRect(5, yPos, 310, 1, GREY);
  yPos += 5;
  
  // Display pools
  for (int i = 0; i < sysData.poolCount && i < 4; i++) {
    // Pool name
    drawString(10, yPos, sysData.pools[i].name, WHITE);
    
    // Capacity
    drawString(80, yPos, sysData.pools[i].capacity, WHITE);
    
    // Usage
    drawString(160, yPos, sysData.pools[i].usage, ORANGE);
    
    // State
    uint16_t stateColor = (sysData.pools[i].state == "Healthy") ? GREEN : RED;
    drawString(220, yPos, sysData.pools[i].state, stateColor);
    
    yPos += 18;
    
    // Separator line
    if (i < sysData.poolCount - 1) {
      fillRect(5, yPos, 310, 1, DARK_GREY);
      yPos += 3;
    }
  }
  
  // If no pools
  if (sysData.poolCount == 0) {
    drawStringMedium(10, yPos + 20, "NO STORAGE POOLS", GREY);
  }
  
  // Navigation hint
  drawString(10, 220, "Button 1: Back  |  Button 3: Next", GREY);
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

void displayCurrentScreen() {
  if (!needsRedraw()) {
    return;
  }
  
  // Always draw header
  drawHeader();
  
  // Display content based on current screen
  switch(currentScreen) {
    case SCREEN_MAIN:
      displayMainScreen();
      break;
    case SCREEN_NETWORK:
      displayNetworkScreen();
      break;
    case SCREEN_STORAGE:
      displayStorageScreen();
      break;
  }
  
  // Update status indicator
  fillRect(280, 8, 8, 8, sysData.hasError ? RED : GREEN);
  
  lastDisplayData = sysData;
  lastScreen = currentScreen;
  forceRedraw = false;
}

void displayMainScreen() {
  
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
  
  Serial.println("Main screen updated with temperature readings");
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
    } else if (command.startsWith("NETWORK:")) {
      Serial.println("Processing NETWORK command...");
      parseNetwork(command);
      forceRedraw = true;
      Serial.println("Network data updated!");
    } else if (command.startsWith("POOL:")) {
      Serial.println("Processing POOL command...");
      parsePool(command);
      forceRedraw = true;
      Serial.println("Pool data updated!");
    } else {
      Serial.println("Unknown command. Supported: UPDATE:, NETWORK:, POOL:");
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

void parseNetwork(String command) {
  // Format: NETWORK:mac_address,ipv4_address,ipv6_address
  command.replace("NETWORK:", "");
  
  int commaIndex = 0;
  int lastIndex = 0;
  int fieldIndex = 0;
  
  while (commaIndex != -1 && fieldIndex < 3) {
    commaIndex = command.indexOf(',', lastIndex);
    String value;
    
    if (commaIndex != -1) {
      value = command.substring(lastIndex, commaIndex);
    } else {
      value = command.substring(lastIndex);
    }
    
    value.trim();
    
    switch (fieldIndex) {
      case 0: sysData.macAddress = value; break;
      case 1: sysData.ipv4Address = value; break;
      case 2: sysData.ipv6Address = value; break;
    }
    
    lastIndex = commaIndex + 1;
    fieldIndex++;
  }
}

void parsePool(String command) {
  // Format: POOL:name,capacity,usage,state
  command.replace("POOL:", "");
  
  // Check if this is a reset command
  if (command == "RESET") {
    sysData.poolCount = 0;
    return;
  }
  
  int commaIndex = 0;
  int lastIndex = 0;
  int fieldIndex = 0;
  
  if (sysData.poolCount < 4) {
    PoolData newPool;
    
    while (commaIndex != -1 && fieldIndex < 4) {
      commaIndex = command.indexOf(',', lastIndex);
      String value;
      
      if (commaIndex != -1) {
        value = command.substring(lastIndex, commaIndex);
      } else {
        value = command.substring(lastIndex);
      }
      
      value.trim();
      
      switch (fieldIndex) {
        case 0: newPool.name = value; break;
        case 1: newPool.capacity = value; break;
        case 2: newPool.usage = value; break;
        case 3: newPool.state = value; break;
      }
      
      lastIndex = commaIndex + 1;
      fieldIndex++;
    }
    
    sysData.pools[sysData.poolCount] = newPool;
    sysData.poolCount++;
  }
}