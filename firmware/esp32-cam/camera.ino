#include <WiFi.h>
#include <WiFiClientSecure.h>
#include "esp_camera.h"
#include <UniversalTelegramBot.h>
#include <ArduinoJson.h>
#include "soc/soc.h"           
#include "soc/rtc_cntl_reg.h"  

// =======================
// YOUR SETTINGS
// =======================
const char* ssid = "realme";
const char* password = "123456789";
String BOTtoken = "8426786756:AAHxJaUU8FSAvmB1VydfY_P_lSVCF5VHY-o";  
String CHAT_ID = "605136427";     

#define LED_PIN 33 

// Camera Pins (AI Thinker)
#define PWDN_GPIO_NUM     32
#define RESET_GPIO_NUM    -1
#define XCLK_GPIO_NUM     0
#define SIOD_GPIO_NUM     26
#define SIOC_GPIO_NUM     27
#define Y9_GPIO_NUM       35
#define Y8_GPIO_NUM       34
#define Y7_GPIO_NUM       39
#define Y6_GPIO_NUM       36
#define Y5_GPIO_NUM       21
#define Y4_GPIO_NUM       19
#define Y3_GPIO_NUM       18
#define Y2_GPIO_NUM       5
#define VSYNC_GPIO_NUM    25
#define HREF_GPIO_NUM     23
#define PCLK_GPIO_NUM     22

WiFiClientSecure clientTCP;
UniversalTelegramBot bot(BOTtoken, clientTCP);

camera_fb_t * fb = NULL;
size_t currentByte = 0;
size_t fb_length = 0;

bool isMoreDataAvailable() { return (fb_length - currentByte); }

uint8_t getNextByte() {
  currentByte++;
  return (fb->buf[currentByte - 1]);
}

void setup() {
  WRITE_PERI_REG(RTC_CNTL_BROWN_OUT_REG, 0); 
  
  pinMode(LED_PIN, OUTPUT);
  digitalWrite(LED_PIN, HIGH); 

  Serial.begin(9600);   
  delay(10); 

  camera_config_t config;
  config.ledc_channel = LEDC_CHANNEL_0;
  config.ledc_timer = LEDC_TIMER_0;
  config.pin_d0 = Y2_GPIO_NUM;
  config.pin_d1 = Y3_GPIO_NUM;
  config.pin_d2 = Y4_GPIO_NUM;
  config.pin_d3 = Y5_GPIO_NUM;
  config.pin_d4 = Y6_GPIO_NUM;
  config.pin_d5 = Y7_GPIO_NUM;
  config.pin_d6 = Y8_GPIO_NUM;
  config.pin_d7 = Y9_GPIO_NUM;
  config.pin_xclk = XCLK_GPIO_NUM;
  config.pin_pclk = PCLK_GPIO_NUM;
  config.pin_vsync = VSYNC_GPIO_NUM;
  config.pin_href = HREF_GPIO_NUM;
  config.pin_sscb_sda = SIOD_GPIO_NUM;
  config.pin_sscb_scl = SIOC_GPIO_NUM;
  config.pin_pwdn = PWDN_GPIO_NUM;
  config.pin_reset = RESET_GPIO_NUM;
  config.xclk_freq_hz = 20000000;
  config.pixel_format = PIXFORMAT_JPEG;
  config.frame_size = FRAMESIZE_VGA; 
  config.jpeg_quality = 12;          
  config.fb_count = 1;
  
  esp_camera_init(&config);
  delay(2000); 

  WiFi.mode(WIFI_STA);
  WiFi.setSleep(false); 
  WiFi.begin(ssid, password);
  
  while (WiFi.status() != WL_CONNECTED) {
    digitalWrite(LED_PIN, LOW); 
    delay(200);
    digitalWrite(LED_PIN, HIGH);
    delay(200);
  }
  
  digitalWrite(LED_PIN, LOW); 
  clientTCP.setInsecure();
  configTime(0, 0, "pool.ntp.org", "time.nist.gov");
}

void sendPhotoToTelegram() {
  // 1. DUMMY FRAME FIX: Flushes the "green image" hardware bug out of the sensor
  camera_fb_t * dummy = esp_camera_fb_get();
  if(dummy) esp_camera_fb_return(dummy);
  delay(100); 
  
  // 2. REAL FRAME
  fb = esp_camera_fb_get();
  if(!fb) {
    Serial.println("ERROR"); // Tell Pico the camera crashed
    return;
  }
  
  digitalWrite(LED_PIN, HIGH); 
  currentByte = 0;
  fb_length = fb->len;
  
  bot.sendPhotoByBinary(CHAT_ID, "image/jpeg", fb->len,
                        isMoreDataAvailable, getNextByte,
                        nullptr, nullptr);

  esp_camera_fb_return(fb);
  
  // 3. MEMORY LEAK FIX: Force close the TCP socket to free up RAM!
  clientTCP.stop(); 
  
  digitalWrite(LED_PIN, LOW); 
}

void loop() {
  if (Serial.available()) {
    String command = Serial.readStringUntil('\n');
    
    // THE FIX: Use indexOf to look for SNAP, ignoring any weird hidden characters
    if (command.indexOf("SNAP") >= 0) { 
      Serial.println("UPLOADING"); // Genuine handshake start
      sendPhotoToTelegram();
      Serial.println("DONE");      // Genuine handshake finish
    }
  }
}