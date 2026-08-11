/*
=============================================================
 DIAGNÓSTICO 2 — SERVO SG90
=============================================================

 O que esse teste faz:
   Move o servo para 3 posições: esquerda, centro, direita.
   Repete em loop.

 Como usar:
   1. Observe o servo girando nas 3 posições
   2. O Serial Monitor mostra qual posição está sendo
      executada
   3. O movimento deve ser suave e sem travamento

 Conexões a confirmar:
   Servo fio MARROM (GND) → GND do ESP32
   Servo fio VERMELHO (V+) → 3V3 do ESP32
   Servo fio LARANJA (PWM) → GPIO13

 Observação:
   No robô físico o servo vai alimentado pelo 5V do L298N.
   Para este teste isolado, 3V3 é suficiente para confirmar
   o funcionamento, mas o movimento pode ser mais fraco.

=============================================================
*/

#include <ESP32Servo.h>

const int SERVO_PIN = 13;

Servo meuServo;

void setup()
{
  Serial.begin(115200);

  meuServo.setPeriodHertz(50);
  meuServo.attach(SERVO_PIN, 500, 2400);

  Serial.println();
  Serial.println("=== TESTE SERVO SG90 ===");
  Serial.println();
}

void loop()
{
  Serial.println("Posição: ESQUERDA (30°)");
  meuServo.write(30);
  delay(1500);

  Serial.println("Posição: CENTRO (90°)");
  meuServo.write(90);
  delay(1500);

  Serial.println("Posição: DIREITA (150°)");
  meuServo.write(150);
  delay(1500);

  Serial.println("Posição: CENTRO (90°)");
  meuServo.write(90);
  delay(1500);

  Serial.println();
}
