/*
=============================================================
 DIAGNÓSTICO 3 — L298N + MOTORES
=============================================================

 O que esse teste faz:
   Testa cada motor individualmente e depois os dois juntos,
   nas duas direções. Para entre cada movimento.

 Como usar:
   1. Deixe o robô apoiado (rodas no ar) ou no chão
   2. Acompanhe o Serial Monitor para saber qual motor
      deveria estar girando
   3. Confirme se o motor certo está girando na direção certa

 Conexões a confirmar:
   L298N IN1  → GPIO22
   L298N IN2  → GPIO21
   L298N ENA  → GPIO23
   L298N IN3  → GPIO19
   L298N IN4  → GPIO18
   L298N ENB  → GPIO5
   L298N 12V  → positivo das pilhas (6V)
   L298N GND  → negativo das pilhas + GND do ESP32
   L298N 5V   → VIN do ESP32
   Motor esq. → OUT1 e OUT2 do L298N
   Motor dir. → OUT3 e OUT4 do L298N

 Jumper do L298N:
   O jumper de 12V deve estar COLOCADO para que a saída
   de 5V funcione e alimente o ESP32.

=============================================================
*/

// Pinos motor esquerdo
const int IN1 = 22;
const int IN2 = 21;
const int ENA = 23;

// Pinos motor direito
const int IN3 = 19;
const int IN4 = 18;
const int ENB = 5;

// Velocidade do teste (0-255)
const int VEL = 200;

// Tempo de cada movimento em ms
const int TEMPO = 2000;

void setup()
{
  Serial.begin(115200);

  pinMode(IN1, OUTPUT);
  pinMode(IN2, OUTPUT);
  pinMode(ENA, OUTPUT);
  pinMode(IN3, OUTPUT);
  pinMode(IN4, OUTPUT);
  pinMode(ENB, OUTPUT);

  pararTudo();

  Serial.println();
  Serial.println("=== TESTE L298N + MOTORES ===");
  Serial.println("Iniciando em 2 segundos...");
  Serial.println();
  delay(2000);
}

void loop()
{
  // ----------------------------------------------------------
  // MOTOR ESQUERDO — frente
  // ----------------------------------------------------------

  Serial.println("Motor ESQUERDO girando para FRENTE...");
  digitalWrite(IN1, HIGH);
  digitalWrite(IN2, LOW);
  analogWrite(ENA, VEL);
  delay(TEMPO);
  pararTudo();
  delay(500);

  // ----------------------------------------------------------
  // MOTOR ESQUERDO — ré
  // ----------------------------------------------------------

  Serial.println("Motor ESQUERDO girando para RÉ...");
  digitalWrite(IN1, LOW);
  digitalWrite(IN2, HIGH);
  analogWrite(ENA, VEL);
  delay(TEMPO);
  pararTudo();
  delay(500);

  // ----------------------------------------------------------
  // MOTOR DIREITO — frente
  // ----------------------------------------------------------

  Serial.println("Motor DIREITO girando para FRENTE...");
  digitalWrite(IN3, HIGH);
  digitalWrite(IN4, LOW);
  analogWrite(ENB, VEL);
  delay(TEMPO);
  pararTudo();
  delay(500);

  // ----------------------------------------------------------
  // MOTOR DIREITO — ré
  // ----------------------------------------------------------

  Serial.println("Motor DIREITO girando para RÉ...");
  digitalWrite(IN3, LOW);
  digitalWrite(IN4, HIGH);
  analogWrite(ENB, VEL);
  delay(TEMPO);
  pararTudo();
  delay(500);

  // ----------------------------------------------------------
  // OS DOIS JUNTOS — frente
  // ----------------------------------------------------------

  Serial.println("OS DOIS MOTORES girando para FRENTE...");
  digitalWrite(IN1, HIGH); digitalWrite(IN2, LOW);
  digitalWrite(IN3, HIGH); digitalWrite(IN4, LOW);
  analogWrite(ENA, VEL);
  analogWrite(ENB, VEL);
  delay(TEMPO);
  pararTudo();
  delay(500);

  // ----------------------------------------------------------
  // OS DOIS JUNTOS — ré
  // ----------------------------------------------------------

  Serial.println("OS DOIS MOTORES girando para RÉ...");
  digitalWrite(IN1, LOW); digitalWrite(IN2, HIGH);
  digitalWrite(IN3, LOW); digitalWrite(IN4, HIGH);
  analogWrite(ENA, VEL);
  analogWrite(ENB, VEL);
  delay(TEMPO);
  pararTudo();

  Serial.println();
  Serial.println("--- Ciclo completo. Repetindo em 3s... ---");
  Serial.println();
  delay(3000);
}

void pararTudo()
{
  analogWrite(ENA, 0);
  analogWrite(ENB, 0);
  digitalWrite(IN1, LOW);
  digitalWrite(IN2, LOW);
  digitalWrite(IN3, LOW);
  digitalWrite(IN4, LOW);
  Serial.println("PARADO.");
  delay(200);
}
