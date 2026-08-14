/*
=============================================================
 ROBÔ AUTÔNOMO - MODO EXPLORAÇÃO + CÉREBRO LLM
 ESP32-WROOM-32 (corpo) + HC-SR04 + SG90 + L298N

 Wokwi:
   MODO_SIMULACAO = true

 Robô físico:
   MODO_SIMULACAO = false

 [NOVO] Comunicacao com o cerebro (ESP32-S3):
   O corpo detecta a situacao e envia o marcador
   correspondente pela UART2 para o cerebro, que gera
   a frase sarcastica e mostra no display.

 Marcadores enviados:
   <start>      -> ao ligar
   <explore>    -> andando em frente
   <turn_left>  -> curva a esquerda
   <turn_right> -> curva a direita
   <obstacle>   -> obstaculo detectado
   <backup>     -> recuando
   <stuck>      -> encurralado (os dois lados bloqueados)
   <clear>      -> caminho livre de novo apos evasao

=============================================================
*/

#include <ESP32Servo.h>

// ============================================================
// [NOVO] COMUNICAÇÃO COM O CÉREBRO (ESP32-S3)
// ============================================================
// UART2 do WROOM-32: TX=GPIO17 -> RX=GPIO18 do S3.
// So enviamos (o corpo fala, o cerebro escuta).

#include <HardwareSerial.h>
HardwareSerial cerebro(2);   // usa a UART2 do ESP32

// Envia um marcador de situacao para o cerebro.
// Ex: enviarMarcador("<obstacle>");
void enviarMarcador(const char* marcador) {
  cerebro.println(marcador);       // envia o texto + '\n'
  Serial.print("[CEREBRO] enviado: ");
  Serial.println(marcador);        // eco no monitor para depuracao
}

// ============================================================
// CONFIGURAÇÃO PRINCIPAL
// ============================================================

#define MODO_SIMULACAO false

// ============================================================
// PINOS - HC-SR04 E SERVO
// ============================================================

const int TRIG_PIN  = 32;
const int ECHO_PIN  = 33;
const int SERVO_PIN = 13;

// ============================================================
// PINOS - L298N
// Usados somente no robô físico
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
// PINOS - LEDs
// Usados somente no Wokwi
// ============================================================

#if MODO_SIMULACAO

const int LED_FRENTE   = 14;
const int LED_TRAS     = 27;
const int LED_ESQUERDA = 26;
const int LED_DIREITA  = 25;

#endif

// ============================================================
// CONFIGURAÇÃO DO SENSOR
// ============================================================

// Distância mínima considerada segura.
const int DISTANCIA_OBSTACULO = 25;

// ============================================================
// VELOCIDADE
// ============================================================

// Limites para a velocidade aleatória.
// Faixa PWM: 0 a 255.
const int VELOCIDADE_MINIMA = 140;
const int VELOCIDADE_MAXIMA = 220;

// Velocidade usada durante a ré de emergência.
const int VELOCIDADE_RE = 160;

// Velocidade utilizada durante a curva para evitar
// um obstáculo.
const int VELOCIDADE_CURVA_OBSTACULO = 190;

// ============================================================
// TEMPOS DO MODO EXPLORAÇÃO
// ============================================================

// Tempo mínimo e máximo de cada movimento.
const unsigned long DURACAO_MINIMA_MOVIMENTO = 2000;
const unsigned long DURACAO_MAXIMA_MOVIMENTO = 6000;

// Duração mínima e máxima de uma curva aleatória.
const unsigned long DURACAO_MINIMA_CURVA = 300;
const unsigned long DURACAO_MAXIMA_CURVA = 800;

// ============================================================
// TEMPOS DA EVASÃO DE OBSTÁCULO
// ============================================================

const int TEMPO_RECUO = 250;

const int TEMPO_CURVA_OBSTACULO = 450;

// ============================================================
// ÂNGULOS DO SERVO
// ============================================================

const int SERVO_CENTRO   = 90;
const int SERVO_ESQUERDA = 30;
const int SERVO_DIREITA  = 150;

// ============================================================
// OBJETO SERVO
// ============================================================

Servo sensorServo;

// ============================================================
// CONTROLE DO MODO EXPLORAÇÃO
// ============================================================

// Momento em que o movimento atual começou.
unsigned long inicioMovimento = 0;

// Duração escolhida aleatoriamente para o movimento atual.
unsigned long duracaoMovimento = 0;

// Velocidade escolhida aleatoriamente.
int velocidadeAtual = 0;

// Movimento atual.
// 0 = frente
// 1 = esquerda
// 2 = direita
int movimentoAtual = 0;

// Guarda a última curva escolhida.
// Usado para evitar que o robô fique repetindo
// o mesmo lado com muita frequência.
//
// 0 = nenhuma
// 1 = esquerda
// 2 = direita
int ultimaCurva = 0;

// ============================================================
// [NOVO] CONTROLE DOS MARCADORES <clear> E <stuck>
// ============================================================
// Flag que lembra se o robô estava lidando com um obstaculo.
// Serve para detectar a TRANSICAO de volta ao caminho livre
// (para enviar <clear> so uma vez, nao a cada loop).
bool estavaEvitandoObstaculo = false;

// ============================================================
// SETUP
// ============================================================

void setup()
{
  Serial.begin(115200);

  // [NOVO] Inicializa a comunicacao com o cerebro (S3)
  // 9600 baud, TX=17, RX=16 (RX nao usado, mas exigido pela API)
  cerebro.begin(9600, SERIAL_8N1, 16, 17);

  Serial.println();
  Serial.println("========================================");
  Serial.println("       ROBÔ AUTÔNOMO ESP32");
  Serial.println("          MODO EXPLORAÇÃO");
  Serial.println("========================================");

  #if MODO_SIMULACAO
    Serial.println("MODO: SIMULAÇÃO WOKWI");
  #else
    Serial.println("MODO: ROBÔ FÍSICO");
  #endif

  Serial.println("========================================");
  Serial.println();

  // ----------------------------------------------------------
  // Inicializa o gerador de números aleatórios.
  // ----------------------------------------------------------

  randomSeed(micros());

  // ----------------------------------------------------------
  // HC-SR04
  // ----------------------------------------------------------

  pinMode(TRIG_PIN, OUTPUT);
  pinMode(ECHO_PIN, INPUT);

  // ----------------------------------------------------------
  // L298N
  // ----------------------------------------------------------

  #if !MODO_SIMULACAO

    pinMode(IN1, OUTPUT);
    pinMode(IN2, OUTPUT);

    pinMode(IN3, OUTPUT);
    pinMode(IN4, OUTPUT);

    pinMode(ENA, OUTPUT);
    pinMode(ENB, OUTPUT);

  #endif

  // ----------------------------------------------------------
  // LEDs
  // ----------------------------------------------------------

  #if MODO_SIMULACAO

    pinMode(LED_FRENTE, OUTPUT);
    pinMode(LED_TRAS, OUTPUT);
    pinMode(LED_ESQUERDA, OUTPUT);
    pinMode(LED_DIREITA, OUTPUT);

  #endif

  // ----------------------------------------------------------
  // Servo
  // ----------------------------------------------------------

  sensorServo.setPeriodHertz(50);

  sensorServo.attach(
    SERVO_PIN,
    500,
    2400
  );

  // ----------------------------------------------------------
  // Estado inicial
  // ----------------------------------------------------------

  parar();

  sensorServo.write(SERVO_CENTRO);

  delay(1000);

  // [NOVO] Avisa o cerebro que o robô acordou
  enviarMarcador("<start>");
  delay(500);   // dá um tempo para o cerebro gerar a frase de boas-vindas

  // ----------------------------------------------------------
  // Primeiro movimento aleatório
  // ----------------------------------------------------------

  iniciarNovoMovimento();

  Serial.println("Sistema iniciado.");
  Serial.println();
}


// ============================================================
// LOOP PRINCIPAL
// ============================================================

void loop()
{
  // ----------------------------------------------------------
  // PRIMEIRA PRIORIDADE:
  // VERIFICAR OBSTÁCULO
  // ----------------------------------------------------------

  float distancia = medirDistancia();

  Serial.print("Distância: ");
  Serial.print(distancia);
  Serial.println(" cm");

  // ----------------------------------------------------------
  // Se existe obstáculo:
  //
  // A exploração aleatória é interrompida.
  // A evasão tem prioridade.
  // ----------------------------------------------------------

  if (distancia <= DISTANCIA_OBSTACULO)
  {
    evitarObstaculo();

    // Depois da evasão, começa um novo movimento
    // aleatório.
    iniciarNovoMovimento();

    return;
  }

  // ----------------------------------------------------------
  // [NOVO] Se chegou aqui, o caminho esta livre.
  // Se o robô ESTAVA evitando um obstaculo no ciclo
  // anterior, isso e uma TRANSICAO para caminho livre:
  // envia <clear> uma unica vez.
  // ----------------------------------------------------------

  if (estavaEvitandoObstaculo)
  {
    enviarMarcador("<clear>");
    estavaEvitandoObstaculo = false;
  }

  // ----------------------------------------------------------
  // Se não existe obstáculo:
  //
  // Continua o modo exploração.
  // ----------------------------------------------------------

  executarMovimentoAtual();

  // ----------------------------------------------------------
  // Verifica se o tempo escolhido para o movimento
  // terminou.
  // ----------------------------------------------------------

  if (millis() - inicioMovimento >= duracaoMovimento)
  {
    iniciarNovoMovimento();
  }

  // Pequeno intervalo para não sobrecarregar o loop.
  delay(50);
}


// ============================================================
// INICIAR NOVO MOVIMENTO ALEATÓRIO
// ============================================================

void iniciarNovoMovimento()
{
  // ----------------------------------------------------------
  // Escolhe uma nova velocidade aleatória.
  //
  // random(min, max) não inclui o valor máximo.
  // ----------------------------------------------------------

  velocidadeAtual = random(
    VELOCIDADE_MINIMA,
    VELOCIDADE_MAXIMA + 1
  );

  // ----------------------------------------------------------
  // Sorteia o tipo de movimento.
  //
  // 0 = frente
  // 1 = esquerda
  // 2 = direita
  //
  // Probabilidades:
  //
  // Frente  = 50%
  // Esquerda = 25%
  // Direita  = 25%
  // ----------------------------------------------------------

  int sorteio = random(100);

  if (sorteio < 50)
  {
    movimentoAtual = 0;
  }
  else if (sorteio < 75)
  {
    movimentoAtual = 1;
  }
  else
  {
    movimentoAtual = 2;
  }

  // ----------------------------------------------------------
  // Se escolheu esquerda ou direita, evita repetir
  // a mesma curva duas vezes seguidas.
  // ----------------------------------------------------------

  if (movimentoAtual == 1 && ultimaCurva == 1)
  {
    movimentoAtual = 2;
  }

  if (movimentoAtual == 2 && ultimaCurva == 2)
  {
    movimentoAtual = 1;
  }

  // ----------------------------------------------------------
  // Registra a curva escolhida.
  // ----------------------------------------------------------

  if (movimentoAtual == 1)
  {
    ultimaCurva = 1;
  }
  else if (movimentoAtual == 2)
  {
    ultimaCurva = 2;
  }

  // ----------------------------------------------------------
  // Escolhe a duração.
  //
  // Frente:
  //   2 a 6 segundos
  //
  // Curvas:
  //   300 a 800 ms
  // ----------------------------------------------------------

  if (movimentoAtual == 0)
  {
    duracaoMovimento = random(
      DURACAO_MINIMA_MOVIMENTO,
      DURACAO_MAXIMA_MOVIMENTO + 1
    );
  }
  else
  {
    duracaoMovimento = random(
      DURACAO_MINIMA_CURVA,
      DURACAO_MAXIMA_CURVA + 1
    );
  }

  // ----------------------------------------------------------
  // Marca o início do movimento.
  // ----------------------------------------------------------

  inicioMovimento = millis();

  // ----------------------------------------------------------
  // Mostra a decisão no Monitor Serial.
  // ----------------------------------------------------------

  Serial.println();
  Serial.println("===== NOVA DECISÃO =====");

  Serial.print("Velocidade: ");
  Serial.println(velocidadeAtual);

  Serial.print("Duração: ");
  Serial.print(duracaoMovimento);
  Serial.println(" ms");

  if (movimentoAtual == 0)
  {
    Serial.println("Decisão: FRENTE");
    enviarMarcador("<explore>");        // [NOVO]
  }
  else if (movimentoAtual == 1)
  {
    Serial.println("Decisão: ESQUERDA");
    enviarMarcador("<turn_left>");      // [NOVO]
  }
  else
  {
    Serial.println("Decisão: DIREITA");
    enviarMarcador("<turn_right>");     // [NOVO]
  }

  Serial.println("========================");
}


// ============================================================
// EXECUTAR MOVIMENTO ATUAL
// ============================================================

void executarMovimentoAtual()
{
  // ----------------------------------------------------------
  // Frente
  // ----------------------------------------------------------

  if (movimentoAtual == 0)
  {
    andarFrente(velocidadeAtual);
  }

  // ----------------------------------------------------------
  // Esquerda
  // ----------------------------------------------------------

  else if (movimentoAtual == 1)
  {
    virarEsquerda(velocidadeAtual);
  }

  // ----------------------------------------------------------
  // Direita
  // ----------------------------------------------------------

  else if (movimentoAtual == 2)
  {
    virarDireita(velocidadeAtual);
  }
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

  // Timeout de 40 ms.
  long duracao = pulseIn(
    ECHO_PIN,
    HIGH,
    40000
  );

  // Sem eco:
  // considera que não existe obstáculo próximo.
  if (duracao == 0)
  {
    return 400;
  }

  // Calcula distância em centímetros.
  float distancia = duracao * 0.0343 / 2.0;

  return distancia;
}


// ============================================================
// MEDIR ESQUERDA
// ============================================================

float medirEsquerda()
{
  Serial.println("Verificando esquerda...");

  sensorServo.write(SERVO_ESQUERDA);

  delay(400);

  float distancia = medirDistancia();

  Serial.print("Esquerda: ");
  Serial.print(distancia);
  Serial.println(" cm");

  return distancia;
}


// ============================================================
// MEDIR DIREITA
// ============================================================

float medirDireita()
{
  Serial.println("Verificando direita...");

  sensorServo.write(SERVO_DIREITA);

  delay(400);

  float distancia = medirDistancia();

  Serial.print("Direita: ");
  Serial.print(distancia);
  Serial.println(" cm");

  return distancia;
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
// DESLIGAR TODOS OS LEDs
// ============================================================

void desligarLeds()
{
  #if MODO_SIMULACAO

    digitalWrite(LED_FRENTE, LOW);
    digitalWrite(LED_TRAS, LOW);
    digitalWrite(LED_ESQUERDA, LOW);
    digitalWrite(LED_DIREITA, LOW);

  #endif
}


// ============================================================
// ANDAR PARA FRENTE
// ============================================================

void andarFrente(int velocidade)
{
  #if MODO_SIMULACAO

    desligarLeds();

    digitalWrite(
      LED_FRENTE,
      HIGH
    );

    Serial.println("[LED] 🟢 FRENTE");

  #else

    // Motor esquerdo
    digitalWrite(IN1, HIGH);
    digitalWrite(IN2, LOW);

    // Motor direito
    digitalWrite(IN3, HIGH);
    digitalWrite(IN4, LOW);

    // Velocidade
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

    digitalWrite(
      LED_TRAS,
      HIGH
    );

    Serial.println("[LED] 🔴 TRÁS");

  #else

    // Motor esquerdo
    digitalWrite(IN1, LOW);
    digitalWrite(IN2, HIGH);

    // Motor direito
    digitalWrite(IN3, LOW);
    digitalWrite(IN4, HIGH);

    // Velocidade
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

    digitalWrite(
      LED_ESQUERDA,
      HIGH
    );

    Serial.println("[LED] 🟡 ESQUERDA");

  #else

    // Motor esquerdo - ré
    digitalWrite(IN1, LOW);
    digitalWrite(IN2, HIGH);

    // Motor direito - frente
    digitalWrite(IN3, HIGH);
    digitalWrite(IN4, LOW);

    // Velocidade
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

    digitalWrite(
      LED_DIREITA,
      HIGH
    );

    Serial.println("[LED] 🔵 DIREITA");

  #else

    // Motor esquerdo - frente
    digitalWrite(IN1, HIGH);
    digitalWrite(IN2, LOW);

    // Motor direito - ré
    digitalWrite(IN3, LOW);
    digitalWrite(IN4, HIGH);

    // Velocidade
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

    // Desliga PWM
    analogWrite(ENA, 0);
    analogWrite(ENB, 0);

    // Desliga entradas
    digitalWrite(IN1, LOW);
    digitalWrite(IN2, LOW);

    digitalWrite(IN3, LOW);
    digitalWrite(IN4, LOW);

  #endif
}


// ============================================================
// EVITAR OBSTÁCULO
// ============================================================

void evitarObstaculo()
{
  Serial.println();
  Serial.println("########################################");
  Serial.println("      OBSTÁCULO DETECTADO!");
  Serial.println("      PRIORIDADE: SEGURANÇA");
  Serial.println("########################################");

  // [NOVO] Avisa o cerebro do obstaculo e marca a flag
  enviarMarcador("<obstacle>");
  estavaEvitandoObstaculo = true;

  // ----------------------------------------------------------
  // 1. PARA
  // ----------------------------------------------------------

  parar();

  delay(200);

  // ----------------------------------------------------------
  // 2. RECUA
  // ----------------------------------------------------------

  Serial.println("Recuando...");

  // [NOVO] Avisa o cerebro que esta recuando
  enviarMarcador("<backup>");

  andarTras(VELOCIDADE_RE);

  delay(TEMPO_RECUO);

  parar();

  delay(200);

  // ----------------------------------------------------------
  // 3. OLHA PARA ESQUERDA
  // ----------------------------------------------------------

  float esquerda = medirEsquerda();

  delay(100);

  // ----------------------------------------------------------
  // 4. OLHA PARA DIREITA
  // ----------------------------------------------------------

  float direita = medirDireita();

  delay(100);

  // ----------------------------------------------------------
  // 5. VOLTA SENSOR AO CENTRO
  // ----------------------------------------------------------

  centralizarSensor();

  // ----------------------------------------------------------
  // DEBUG
  // ----------------------------------------------------------

  Serial.println();
  Serial.println("--- COMPARAÇÃO ---");

  Serial.print("Esquerda = ");
  Serial.print(esquerda);
  Serial.println(" cm");

  Serial.print("Direita  = ");
  Serial.print(direita);
  Serial.println(" cm");

  // ----------------------------------------------------------
  // [NOVO] 5b. VERIFICAR SE ESTA ENCURRALADO
  //
  // Se os DOIS lados estao bloqueados (abaixo do limite),
  // o robô esta preso: envia <stuck>.
  // ----------------------------------------------------------

  if (esquerda <= DISTANCIA_OBSTACULO && direita <= DISTANCIA_OBSTACULO)
  {
    Serial.println("!!! ENCURRALADO — os dois lados bloqueados !!!");
    enviarMarcador("<stuck>");
    // Mesmo preso, ainda tenta o lado menos ruim abaixo.
  }

  // ----------------------------------------------------------
  // 6. ESCOLHE O CAMINHO MAIS LIVRE
  // ----------------------------------------------------------

  if (esquerda > direita)
  {
    Serial.println("Escolha: ESQUERDA");

    virarEsquerda(
      VELOCIDADE_CURVA_OBSTACULO
    );

    delay(TEMPO_CURVA_OBSTACULO);
  }

  else
  {
    Serial.println("Escolha: DIREITA");

    virarDireita(
      VELOCIDADE_CURVA_OBSTACULO
    );

    delay(TEMPO_CURVA_OBSTACULO);
  }

  // ----------------------------------------------------------
  // 7. PARA APÓS A CURVA
  // ----------------------------------------------------------

  parar();

  delay(100);

  Serial.println("Obstáculo contornado.");
  Serial.println("Retornando ao modo exploração.");
  Serial.println();

  // OBS: o <clear> NAO e enviado aqui. Ele e enviado no loop()
  // principal, quando a proxima medicao confirmar que o caminho
  // ficou realmente livre (a flag estavaEvitandoObstaculo).
}
