// Grove water sensor probe for the Seeeduino (ATmega328P) on the ground Pi.
// Prints one line every 250 ms with every Grove base-shield pin, so the
// sensor's port can be found by wetting it:
//   A0..A3 as analog (0-1023), D2..D8 as digital (0/1, INPUT_PULLUP).
// The Grove water sensor's SIG reads HIGH when dry and drops toward LOW when water
// bridges the traces.
// Line format: "A 512 498 503 510 D 1 1 1 1 1 1 1"

void setup() {
  Serial.begin(115200);
  for (int p = 2; p <= 8; p++) pinMode(p, INPUT_PULLUP);
  Serial.println("# water_probe ready");
}

void loop() {
  Serial.print("A");
  for (int a = 0; a <= 3; a++) { Serial.print(' '); Serial.print(analogRead(a)); }
  Serial.print(" D");
  for (int p = 2; p <= 8; p++) { Serial.print(' '); Serial.print(digitalRead(p)); }
  Serial.println();
  delay(250);
}
