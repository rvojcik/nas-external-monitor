# M5Stack NAS Monitor

Advanced Arduino sketch for M5Stack Core featuring high-performance NAS temperature monitoring with modern graphics, visual alerts, and audio feedback.

## ✨ Features

### 📊 Monitoring Capabilities
- **Real-time temperature monitoring** for system and 5 HDDs with visual bars
- **Storage health status** display (Healthy/Problem)
- **Visual temperature bars** with color-coded alerts (Green/Orange/Red)
- **Audio alerts** with triple-beep pattern for critical conditions
- **Automatic timeout detection** with error display after 1 minute

### 🎨 Modern Display Interface
- **High-performance M5GFX graphics** for smooth rendering
- **Optimized 320x240 layout** utilizing full display area
- **Color-coded backgrounds**: Black (normal), Red (alerts/errors)
- **Professional typography** with medium-sized fonts
- **Status indicator** in header showing system health
- **Real-time value updates** with temperature bars

### 🔧 Technical Features
- **Serial command interface** for real-time data updates
- **Efficient redraw system** - only updates when data changes
- **Robust error handling** with visual and audio feedback
- **Hardware-optimized rendering** using M5GFX library
- **Memory efficient** with smart display management

## 🛠️ Hardware Requirements

- **M5Stack Core** (ESP32-based development board)
- **Built-in 320x240 TFT display**
- **Built-in speaker** for audio alerts
- **USB connection** for serial communication and programming

## 📦 Installation

### Prerequisites
1. **Arduino IDE** (latest version recommended)
2. **M5GFX Library** - Install via Arduino Library Manager
3. **ESP32 Board Package** - Add M5Stack boards support

### Installation Steps
1. Clone or download this repository
2. Open `SystemMonitor.ino` in Arduino IDE
3. Install required library: `M5GFX` (Tools → Manage Libraries → Search "M5GFX")
4. Select board: `M5Stack-Core-ESP32` 
5. Upload sketch to your M5Stack Core
6. Open Serial Monitor at **115200 baud**

## 📡 Serial Communication Protocol

### Command Format
Send temperature updates via serial port using this format:

```
UPDATE:system_temp,hdd1_temp,hdd2_temp,hdd3_temp,hdd4_temp,hdd5_temp,storage_state
```

### Example Commands
```bash
# Normal operation - all temperatures safe
UPDATE:45.2,38.1,42.5,39.8,41.2,43.6,Healthy

# High temperature alert - system overheating
UPDATE:55.1,48.3,52.8,46.7,49.2,51.4,Problem

# Mixed conditions - some HDDs warm but acceptable
UPDATE:42.8,35.9,48.4,37.2,36.8,39.1,Healthy
```

### Parameters
- **system_temp**: Main system temperature (°C)
- **hdd1_temp** to **hdd5_temp**: Individual HDD temperatures (°C)
- **storage_state**: Either `Healthy` or `Problem`

## 🎯 Display Behavior

### Background Colors
- **🖤 Black**: Normal operation (all temperatures ≤ 52°C, storage healthy)
- **🔴 Red**: Alert condition (high temperature OR storage problem OR timeout)

### Temperature Bars
- **🟢 Green**: Safe temperature (< 47°C)
- **🟠 Orange**: Warning temperature (47-52°C)
- **🔴 Red**: Critical temperature (> 52°C)

### Audio Alerts
- **Triple beep pattern**: Triggered when temperature exceeds threshold or storage problems detected
- **Automatic**: Plays once when alert condition first occurs

### Status Indicator
- **🟢 Green dot**: System operating normally
- **🟠 Orange dot**: Alert condition active
- **🔴 Red dot**: Error state (no data/timeout)

## ⚙️ Configuration

### Temperature Threshold
Default threshold is **52°C**. To modify:
```cpp
const float TEMP_THRESHOLD = 52.0;  // Change this value
```

### Update Timeout
Default timeout is **60 seconds**. To modify:
```cpp
const unsigned long UPDATE_TIMEOUT = 60000;  // Change this value (milliseconds)
```

### Display Layout
The layout automatically scales to fill the 320x240 display:
- Header: 30px
- Temperature rows: 6 × 26px each  
- Storage status: 28px
- Error message: 22px (when shown)

## 🔧 Technical Specifications

### Performance
- **High-speed rendering** with M5GFX hardware acceleration
- **Optimized memory usage** with efficient drawing routines
- **Real-time updates** with minimal display flicker
- **Responsive interface** with immediate visual feedback

### Communication
- **Serial baud rate**: 115200
- **Update frequency**: Minimum every 60 seconds
- **Command parsing**: Robust with error handling
- **Debug output**: Comprehensive logging via Serial Monitor

## 📋 Display Layout Example

```
┌─────────────────────────────────────────────────────────┐
│  🔷 NAS MONITOR                                    🟢   │ ← Header (30px)
├─────────────────────────────────────────────────────────┤
│  SYSTEM:  ████████████░░░░░░░░░░░░░░░░░░  45.2 C       │ ← Temp rows
│  HDD1:    ██████████░░░░░░░░░░░░░░░░░░░░  38.1 C       │   (26px each)
│  HDD2:    ████████████████░░░░░░░░░░░░░░  42.5 C       │
│  HDD3:    ███████████░░░░░░░░░░░░░░░░░░░  39.8 C       │
│  HDD4:    █████████████░░░░░░░░░░░░░░░░░  41.2 C       │
│  HDD5:    ██████████████████░░░░░░░░░░░░  43.6 C       │
│                                                         │
│  STORAGE: HEALTHY                                       │ ← Storage (28px)
└─────────────────────────────────────────────────────────┘
```

## 🐛 Troubleshooting

### Common Issues
1. **Display appears white/blank**: Check M5GFX library installation
2. **No serial communication**: Verify baud rate (115200) and USB connection
3. **Audio not working**: Check speaker pin configuration (GPIO 25)
4. **Compilation errors**: Ensure M5GFX library is properly installed

### Debug Information
The system provides comprehensive debug output via Serial Monitor:
- Initialization status
- Command parsing results
- Display update notifications  
- Error conditions and alerts

## 📄 License

This project is open source. Feel free to modify and distribute according to your needs.

## 🤝 Contributing

Contributions are welcome! Please feel free to submit issues, feature requests, or pull requests.