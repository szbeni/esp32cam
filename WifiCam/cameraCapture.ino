int camereCaptureAndSend(WiFiClient& client)
{
  auto frame = esp32cam::capture();
  if (frame == nullptr) {
      Serial.println("capture() failure");
      return 0;
  }
  //Serial.println("capture() success: %dx%d %zub\n", frame->getWidth(), frame->getHeight(), frame->size());
  int retval;
  int frameSize = frame->size();
  retval = client.write((char*)(&frameSize), sizeof(frameSize));
  if(retval == 0)
    return 0;
  
  retval = frame->writeTo(client);
  return retval;
  
}
