#include "WifiCam.hpp"
#include <WiFi.h>

static const char* WIFI_SSID = "****";
static const char* WIFI_PASS = "****";

esp32cam::Resolution initialResolution;
#define DEEP_SLEEP_TIME_S 60


//WebServer server(80);
//
//void
//setup()
//{
//  Serial.begin(115200);
//  Serial.println();
//  delay(2000);
//
//  WiFi.persistent(false);
//  WiFi.mode(WIFI_STA);
//  WiFi.begin(WIFI_SSID, WIFI_PASS);
//  if (WiFi.waitForConnectResult() != WL_CONNECTED) {
//    Serial.println("WiFi failure");
//    delay(5000);
//    ESP.restart();
//  }
//  Serial.println("WiFi connected");
//
//  {
//    using namespace esp32cam;
//
//    initialResolution = Resolution::find(1024, 768);
//
//    Config cfg;
//    cfg.setPins(pins::AiThinker);
//    cfg.setResolution(initialResolution);
//    cfg.setJpeg(80);
//
//    bool ok = Camera.begin(cfg);
//    if (!ok) {
//      Serial.println("camera initialize failure");
//      delay(5000);
//      ESP.restart();
//    }
//    Serial.println("camera initialize success");
//  }
//
//  Serial.println("camera starting");
//  Serial.print("http://");
//  Serial.println(WiFi.localIP());
//
//  addRequestHandlers();
//  server.begin();
//}
//
//void
//loop()
//{
//  server.handleClient();
//}
//


const uint16_t port = 61234;
const char * host = "10.1.1.102";
//const char * host = "";
 
void setup()
{
  Serial.begin(115200);

  deepSleepWakeup();

  WiFi.persistent(false);
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASS);
  Serial.println("Connecting to Wifi.");
  int wifiRetry = 0;
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
    if(++wifiRetry > 3)
    {
      Serial.println("\nWiFi Connect Failure.");
      ESP.restart();
      //deepSleepStart(DEEP_SLEEP_TIME_S);
      
    }
  }

  {
    using namespace esp32cam;
    
    initialResolution = Resolution::find(1024, 768);
    
    Config cfg;
    cfg.setPins(pins::AiThinker);
    cfg.setResolution(initialResolution);
    cfg.setJpeg(80);
    
    bool ok = Camera.begin(cfg);
    if (!ok) {
      Serial.println("camera initialize failure");
      delay(5000);
      ESP.restart();
    }
    Serial.println("camera initialize success");
  }
 
}
 
void loop()
{
    WiFiClient client;

    while(1)
    {
      
      bool connected = false;
      int retryCounter = 0;
      while(1)
      {
        connected = client.connect(host, port);
        if (connected)
          break;
        
        Serial.println("Connection to host failed. Retry: " + String(retryCounter));
        delay(500);
        if (++retryCounter > 3)
        {
          Serial.println("Max retry reached.");
          deepSleepStart(DEEP_SLEEP_TIME_S);
        }
            
            
      }

      Serial.println("Connected to server successful!");
      bool streamingFlag = false;
      while(1)
      {
        if (client.available()) {
          char c = client.read();
          Serial.print(c);
          if(c == 'q')
          {
            Serial.println("Stop command received.");
            break;
          }
          else if(c == 's')
          {
            Serial.println("Start streaming");
            streamingFlag = true;
          }
            
        }
        if(streamingFlag)
        {
          int retval = camereCaptureAndSend(client);
          if (retval == 0)
          {
            Serial.println("Connection closed.");
            break;
          }
        }
        delay(1);
      }
      client.stop();
      // 10 sec deep sleep
      deepSleepStart(DEEP_SLEEP_TIME_S);
    }
}
