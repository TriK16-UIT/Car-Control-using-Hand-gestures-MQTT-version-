#include "BluetoothSerial.h"
#include <WiFi.h>
#include <PubSubClient.h>
#include "esp_camera.h"
#include "Base64.h"

//ESP32-CAM-AI-Thinker Pin definition
#define PWDN_GPIO_NUM     32
#define RESET_GPIO_NUM    -1
#define XCLK_GPIO_NUM      0
#define SIOD_GPIO_NUM     26
#define SIOC_GPIO_NUM     27

#define Y9_GPIO_NUM       35
#define Y8_GPIO_NUM       34
#define Y7_GPIO_NUM       39
#define Y6_GPIO_NUM       36
#define Y5_GPIO_NUM       21
#define Y4_GPIO_NUM       19
#define Y3_GPIO_NUM       18
#define Y2_GPIO_NUM        5
#define VSYNC_GPIO_NUM    25
#define HREF_GPIO_NUM     23
#define PCLK_GPIO_NUM     22


String device_name = "ESP32-Client1";
const char* ssid = "";
const char* password = "";
const char* host = "";
String get_info[3];
int j = 0;
String info;

bool bluetooth_disconnect = false;
long start_millis;
long timeout = 10000;

enum connection_stage { PAIRING, WIFI, MQTT, CONNECTED };
enum connection_stage stage = PAIRING;

BluetoothSerial SerialBT;
WiFiClient espClient;
PubSubClient client(espClient);

void setup(){
  Serial.begin(115200);

  initCamera();
}

void initCamera(){
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

  if (psramFound()){
    config.frame_size = FRAMESIZE_UXGA;
    config.jpeg_quality = 10;
    config.fb_count = 2;
  }

  esp_err_t err = esp_camera_init(&config);
  if (err != ESP_OK) {
    Serial.printf("Camera init failed with error 0x%x", err);
    ESP.restart();
  }

  sensor_t * s = esp_camera_sensor_get();
  if (s->id.PID == OV3660_PID) {
    s->set_vflip(s, 1); // flip it back
    s->set_brightness(s, 1); // up the brightness just a bit
    s->set_saturation(s, -2); // lower the saturation
  }

  s->set_framesize(s, FRAMESIZE_QVGA);

  // Turn on Flash
  ledcAttachPin(4, 4);  
  ledcSetup(4, 5000, 8);
}

void init_bluetooth()
{
  SerialBT.begin(device_name);
  Serial.printf("");
  Serial.printf("The device with name \"%s\" is started.\nNow you can pair it with Bluetooth!\n", device_name.c_str());
  bluetooth_disconnect = false;
}

void disconnect_bluetooth()
{
  delay(1000);
  Serial.println("BT stopping");
  delay(1000);
  SerialBT.flush();
  SerialBT.disconnect();
  SerialBT.end();
  Serial.println("BT stopped");
  delay(1000);
  bluetooth_disconnect = true;
}

void handle_bluetooth_data(String info)
{
  for (auto x : info)
  {
    if (x == '|')
    {
      j++;
      continue;  
    }
    else
      get_info[j] = get_info[j] + x;
  }
  ssid = get_info[0].c_str();
  password = get_info[1].c_str();
  host = get_info[2].c_str();
}

bool init_wifi()
{
  Serial.println(ssid);
  Serial.println(password);
  start_millis = millis();
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED)
  {
    delay(500);
    Serial.print(".");
    if (millis() - start_millis > timeout)
      {
        Serial.println("WiFi Connection Failed!");
        WiFi.disconnect(true, true);
        return false;
      }
    }
  Serial.println("WiFi connected!");
  return true;
}

bool init_mqtt()
{
  Serial.println(host);
  client.setServer(host, 1883);
  client.setCallback(callback);
  start_millis = millis();
  while (client.connected())
  {
    if (WiFi.status() != WL_CONNECTED)
    {
      stage = WIFI;
      break;
    }
    delay(500);
    Serial.print(".");
    if (client.connect("ESP32_client1"))
    {
      Serial.println("MQTT Connected!");
      client.subscribe("topic/command");
      return true;
    }
    if (millis() - start_millis > timeout)
    {
      Serial.println("MQTT Connection Failed!");
      WiFi.disconnect(true, true);
      return false;
    }
  }
}

void callback(char* topic, byte* message, unsigned int length) 
{
  Serial.print("Message arrived on topic: ");
  Serial.print(topic);
  Serial.print(". Message: ");
  String messageTemp;
  
  for (int i = 0; i < length; i++) {
    Serial.print((char)message[i]);
    messageTemp += (char)message[i];
  }
  Serial.println();

  // Check if a message is received on the topic "rpi/broadcast"
  if (String(topic) == "topic/command") {
      Serial.println("Topic Accessed!");
  }

  //Similarly add more if statements to check for other subscribed topics 
}

String sendImage() {
  camera_fb_t * fb = NULL;
  fb = esp_camera_fb_get();
  if (!fb) {
    return "Camera capture failed";
  }

  char *input = (char *)fb->buf;
  char output[base64_enc_len(3)];
  String imageFile = "data:image/jpeg;base64,";
  for (int i=0; i<fb->len; i++) {
    base64_encode(output, (input++), 3);
    if (i%3==0) imageFile += String(output);
  }
  int fbLen = imageFile.length();

  client.beginPublish("topic/cam", fbLen, true);
  String str = "";
  for (size_t n=0;n<fbLen;n=n+2048) {
      if (n+2048<fbLen) {
        str = imageFile.substring(n, n+2048);
        client.write((uint8_t*)str.c_str(), 2048);
      }
      else if (fbLen%2048>0) {
        size_t remainder = fbLen%2048;
        str = imageFile.substring(n, n+remainder);
        client.write((uint8_t*)str.c_str(), remainder);
      }
  } 
  client.endPublish();
  esp_camera_fb_return(fb);
  return "";
}

void loop() {
  delay(20);
  switch (stage)
  {
    case PAIRING:
      if (!bluetooth_disconnect)
        init_bluetooth();
      Serial.println("Waiting for SSID provided by server... ");
      Serial.println("Waiting for password provided by server... ");
      while (info == "")
      {
        if (SerialBT.available()) {
        info = SerialBT.readString();
        }
      }
      handle_bluetooth_data(info);
      if (ssid == "" || host == "")
        stage = PAIRING;
      else
        stage = WIFI;
      break;

    case WIFI:
      Serial.println("Waiting for Wi-Fi connection");
      if (init_wifi())
      {
        Serial.println("");
        Serial.println("Wifi connected");
        Serial.print("IP address: ");
        Serial.println(WiFi.localIP());
        disconnect_bluetooth();
        stage = MQTT;
      }
      else
      {
        Serial.println("Wi-Fi connection failed");
        delay(2000);
        stage = PAIRING;  
      }
      break;

    case MQTT:
      Serial.println("Waiting for MQTT connection");
      if (init_mqtt())
        stage = CONNECTED;
      else
        stage = PAIRING;
      break;

    case CONNECTED:
      if (!client.connected())
      {
        Serial.println("MQTT Disconnected");
        WiFi.disconnect(true, true);
        stage = PAIRING;
      }
      String feedback = sendImage();
      client.loop();
      break;
  }
}


