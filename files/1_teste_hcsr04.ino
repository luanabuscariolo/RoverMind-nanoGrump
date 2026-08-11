/*
=============================================================
 DIAGNÓSTICO 1 — HC-SR04
=============================================================

 O que esse teste faz:
   Mede a distância continuamente e mostra no Serial Monitor.

 Como usar:
   1. Abra o Serial Monitor na Arduino IDE (115200 baud)
   2. Coloque a mão na frente do sensor
   3. A distância deve mudar conforme você aproxima
      ou afasta a mão

 Conexões a confirmar:
   HC-SR04 VCC  → 3V3 do ESP32
   HC-SR04 GND  → GND do ESP32
   HC-SR04 TRIG → GPIO32
   HC-SR04 ECHO → GPIO33

=============================================================
*/

const int TRIG = 32;
const int ECHO = 33;

void setup()
{
  Serial.begin(115200);
  pinMode(TRIG, OUTPUT);
  pinMode(ECHO, INPUT);

  Serial.println();
  Serial.println("=== TESTE HC-SR04 ===");
  Serial.println("Aproxime a mão do sensor...");
  Serial.println();
}

void loop()
{
  // Dispara o pulso
  digitalWrite(TRIG, LOW);
  delayMicroseconds(2);
  digitalWrite(TRIG, HIGH);
  delayMicroseconds(10);
  digitalWrite(TRIG, LOW);

  // Mede o eco
  long duracao = pulseIn(ECHO, HIGH, 30000);

  if (duracao == 0)
  {
    Serial.println("Sem eco — nada detectado (ou sensor desconectado)");
  }
  else
  {
    float distancia = duracao * 0.0343 / 2.0;
    Serial.print("Distância: ");
    Serial.print(distancia);
    Serial.println(" cm");
  }

  delay(300);
}
