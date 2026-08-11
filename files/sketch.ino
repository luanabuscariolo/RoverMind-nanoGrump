/*
=============================================================
 ROBÔ AUTÔNOMO - ESP32 + HC-SR04 + SG90 + L298N
=============================================================

 Para simular no Wokwi:   MODO_SIMULACAO true
 Para o robô físico:      MODO_SIMULACAO false

=============================================================
*/

#include <ESP32Servo.h>

// ============================================================
// FLAG PRINCIPAL — mude apenas esta linha
// ============================================================

#define MODO_SIMULACAO true

// ============================================================
// PINOS — HC-SR04 e Servo (iguais nos dois modos)
// ============================================================

const int TRIG_PIN  = 32;
const int ECHO_PIN  = 33;
const int SERVO_PIN = 13;

// ============================================================
// PINOS — L298N (usados apenas no robô físico)
// ============================================================

#if !MODO_SIMULACAO
  const int ENA = 23;
  const int IN1 = 22;
  const int IN2 = 21;
  const int ENB = 5;
  const int IN3 = 19;
  const int IN4 = 18;
#endif

// ============================================================
// PINOS — LEDs (usados apenas no Wokwi)
// ============================================================

#if MODO_SIMULACAO
  const int LED_FRENTE   = 14;
  const int LED_TRAS     = 27;
  const int LED_ESQUERDA = 26;
  const int LED_DIREITA  = 25;
#endif

// ============================================================
// CONFIGURAÇÕES DO ROBÔ
// ============================================================

const int VELOCIDADE_NORMAL   = 190;
const int VELOCIDADE_RE       = 160;
const int VELOCIDADE_CURVA    = 190;
const int DISTANCIA_OBSTACULO = 25;
const int TEMPO_RECUO         = 250;
const int TEMPO_CURVA         = 450;

// ============================================================
// ÂNGULOS DO SERVO
// ============================================================

const int SERVO_CENTRO   = 90;
const int SERVO_ESQUERDA = 150;
const int SERVO_DIREITA  = 30;

// ============================================================
// OBJETO DO SERVO
// ============================================================

Servo sensorServo;

// ============================================================
// SETUP
// ============================================================

void setup()
{
  Serial.begin(115200);
  Serial.println();
  Serial.println("=================================");

  #if MODO_SIMULACAO
    Serial.println("   MODO: SIMULAÇÃO (Wokwi)");
  #else
    Serial.println("   MODO: ROBÔ FÍSICO");
  #endif

  Serial.println("=================================");

  // HC-SR04
  pinMode(TRIG_PIN, OUTPUT);
  pinMode(ECHO_PIN, INPUT);

  // L298N (robô físico)
  #if !MODO_SIMULACAO
    pinMode(IN1, OUTPUT);
    pinMode(IN2, OUTPUT);
    pinMode(IN3, OUTPUT);
    pinMode(IN4, OUTPUT);
    pinMode(ENA, OUTPUT);
    pinMode(ENB, OUTPUT);
  #endif

  // LEDs (Wokwi)
  #if MODO_SIMULACAO
    pinMode(LED_FRENTE,   OUTPUT);
    pinMode(LED_TRAS,     OUTPUT);
    pinMode(LED_ESQUERDA, OUTPUT);
    pinMode(LED_DIREITA,  OUTPUT);
  #endif

  // Servo
  sensorServo.setPeriodHertz(50);
  sensorServo.attach(SERVO_PIN, 500, 2400);

  parar();
  sensorServo.write(SERVO_CENTRO);
  delay(1000);

  Serial.println("Sistema iniciado.");
}

// ============================================================
// LOOP PRINCIPAL
// ============================================================

void loop()
{
  float distancia = medirDistancia();

  Serial.print("Distância frontal: ");
  Serial.print(distancia);
  Serial.println(" cm");

  if (distancia > DISTANCIA_OBSTACULO)
  {
    andarFrente(VELOCIDADE_NORMAL);
  }
  else
  {
    evitarObstaculo();
  }

  delay(50);
}

// ============================================================
// MEDIR DISTÂNCIA
// ============================================================

float medirDistancia()
{
  digitalWrite(TRIG_PIN, LOW);
  delayMicroseconds(2);
  digitalWrite(TRIG_PIN, HIGH);
  delayMicroseconds(10);
  digitalWrite(TRIG_PIN, LOW);

  long duracao = pulseIn(ECHO_PIN, HIGH, 30000);

  if (duracao == 0) return 400;

  return duracao * 0.0343 / 2.0;
}

// ============================================================
// OLHAR PARA A ESQUERDA
// ============================================================

float medirEsquerda()
{
  Serial.println("Verificando esquerda...");
  sensorServo.write(SERVO_ESQUERDA);
  delay(400);
  float d = medirDistancia();
  Serial.print("Esquerda: "); Serial.print(d); Serial.println(" cm");
  return d;
}

// ============================================================
// OLHAR PARA A DIREITA
// ============================================================

float medirDireita()
{
  Serial.println("Verificando direita...");
  sensorServo.write(SERVO_DIREITA);
  delay(400);
  float d = medirDistancia();
  Serial.print("Direita: "); Serial.print(d); Serial.println(" cm");
  return d;
}

// ============================================================
// CENTRALIZAR SENSOR
// ============================================================

void centralizarSensor()
{
  sensorServo.write(SERVO_CENTRO);
  delay(300);
}

// ============================================================
// DESLIGAR TODOS OS LEDs (interno)
// ============================================================

void desligarLeds()
{
  #if MODO_SIMULACAO
    digitalWrite(LED_FRENTE,   LOW);
    digitalWrite(LED_TRAS,     LOW);
    digitalWrite(LED_ESQUERDA, LOW);
    digitalWrite(LED_DIREITA,  LOW);
  #endif
}

// ============================================================
// ANDAR PARA FRENTE
// ============================================================

void andarFrente(int velocidade)
{
  #if MODO_SIMULACAO
    desligarLeds();
    digitalWrite(LED_FRENTE, HIGH);
    Serial.println("[LED] 🟢 FRENTE");
  #else
    digitalWrite(IN1, HIGH); digitalWrite(IN2, LOW);
    digitalWrite(IN3, HIGH); digitalWrite(IN4, LOW);
    analogWrite(ENA, velocidade);
    analogWrite(ENB, velocidade);
  #endif
}

// ============================================================
// ANDAR PARA TRÁS
// ============================================================

void andarTras(int velocidade)
{
  #if MODO_SIMULACAO
    desligarLeds();
    digitalWrite(LED_TRAS, HIGH);
    Serial.println("[LED] 🔴 TRÁS");
  #else
    digitalWrite(IN1, LOW); digitalWrite(IN2, HIGH);
    digitalWrite(IN3, LOW); digitalWrite(IN4, HIGH);
    analogWrite(ENA, velocidade);
    analogWrite(ENB, velocidade);
  #endif
}

// ============================================================
// VIRAR PARA ESQUERDA
// ============================================================

void virarEsquerda(int velocidade)
{
  #if MODO_SIMULACAO
    desligarLeds();
    digitalWrite(LED_ESQUERDA, HIGH);
    Serial.println("[LED] 🟡 ESQUERDA");
  #else
    digitalWrite(IN1, LOW);  digitalWrite(IN2, HIGH);
    digitalWrite(IN3, HIGH); digitalWrite(IN4, LOW);
    analogWrite(ENA, velocidade);
    analogWrite(ENB, velocidade);
  #endif
}

// ============================================================
// VIRAR PARA DIREITA
// ============================================================

void virarDireita(int velocidade)
{
  #if MODO_SIMULACAO
    desligarLeds();
    digitalWrite(LED_DIREITA, HIGH);
    Serial.println("[LED] 🔵 DIREITA");
  #else
    digitalWrite(IN1, HIGH); digitalWrite(IN2, LOW);
    digitalWrite(IN3, LOW);  digitalWrite(IN4, HIGH);
    analogWrite(ENA, velocidade);
    analogWrite(ENB, velocidade);
  #endif
}

// ============================================================
// PARAR
// ============================================================

void parar()
{
  #if MODO_SIMULACAO
    desligarLeds();
    Serial.println("[LED] ⬛ PARADO");
  #else
    analogWrite(ENA, 0);
    analogWrite(ENB, 0);
    digitalWrite(IN1, LOW); digitalWrite(IN2, LOW);
    digitalWrite(IN3, LOW); digitalWrite(IN4, LOW);
  #endif
}

// ============================================================
// EVITAR OBSTÁCULO
// ============================================================

void evitarObstaculo()
{
  Serial.println();
  Serial.println(">>> OBSTÁCULO DETECTADO <<<");

  parar();
  delay(200);

  Serial.println("Recuando...");
  andarTras(VELOCIDADE_RE);
  delay(TEMPO_RECUO);
  parar();
  delay(200);

  float esquerda = medirEsquerda();
  delay(100);
  float direita  = medirDireita();
  delay(100);

  centralizarSensor();

  Serial.println();
  Serial.print("Esquerda = "); Serial.print(esquerda); Serial.println(" cm");
  Serial.print("Direita  = "); Serial.print(direita);  Serial.println(" cm");

  if (esquerda > direita)
  {
    Serial.println("Escolha: ESQUERDA");
    virarEsquerda(VELOCIDADE_CURVA);
    delay(TEMPO_CURVA);
  }
  else
  {
    Serial.println("Escolha: DIREITA");
    virarDireita(VELOCIDADE_CURVA);
    delay(TEMPO_CURVA);
  }

  parar();
  delay(100);

  Serial.println("Continuando...");
  Serial.println();
}
