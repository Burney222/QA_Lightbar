// Parallel read of the linear sensor array TSL1402R (= the sensor with 256 photodiodes)
// modified to work with TSL2014 896 channel array by B. Leverington
//-------------------------------------------------------------------------------------

// Define various ADC prescaler:
const unsigned char PS_32 = (1 << ADPS2) | (1 << ADPS0);
const unsigned char PS_128 = (1 << ADPS2) | (1 << ADPS1) | (1 << ADPS0);
int CLKpin = 4;    // <-- Arduino pin delivering the clock pulses to pin 3 (CLK) of the TSL1402R / pin 6 of TSL2014
int SIpin = 6;     // <-- Arduino pin delivering the SI (serial-input) pulse to pin 2 of the TSL1402R / pin 2 of TSL2014
int AOpin1 = 1;    // <-- Arduino pin connected to pin 4 (analog output 1)of the TSL1402R / pin 3 of TSL2014
uint8_t IntArray[896]; // <-- the array where the readout of the photodiodes is stored, as integers (not enough memory for longer values)
int integrationtime = 0;   // <-- Variable to store the integration time
int ledbrightness = 0;     // <-- Variable to store the led brightness level
unsigned int milliseconds = 0;  // <-- Temp. variable to measure the integrationtime


void setup() 
{
  // Initialize two Arduino pins as digital output:
  pinMode(CLKpin, OUTPUT); 
  pinMode(SIpin, OUTPUT);  

  // To set up the ADC, first remove bits set by Arduino library, then choose 
  // a prescaler: PS_16, PS_32, PS_64 or PS_128:
  ADCSRA &= ~PS_128;  
  ADCSRA |= PS_32; // <-- Using PS_32 makes a single ADC conversion take ~30 us

  // Next, assert default setting:
  analogReference(DEFAULT);
  pinMode(5, OUTPUT);  
  // Set all IO pins low:
  for( int i=0; i< 14; i++ )
  {
      digitalWrite(i, LOW);  
  }

  // Clock out any existing SI pulse through the ccd register:
  for(int i=0;i< 900;i++)
  {
      ClockPulse(); 
  }

  // Create a new SI pulse and clock out that same SI pulse through the sensor register:
  digitalWrite(SIpin, HIGH);
  ClockPulse(); 
  digitalWrite(SIpin, LOW);
  for(int i=0;i< 900;i++)
  {
      ClockPulse(); 
  }

  Serial.begin(115200); // make sure this matches the COM port setting in the OS
//  Serial.println("--- Start Serial Monitor SEND_RCVE ---");
 
}

void loop() 
{     
      // Stop the ongoing integration of light quanta from each photodiode by clocking in a SI pulse 
      // into the sensors register and reading out the pixels
      digitalWrite(SIpin, HIGH);
      ClockPulse();
      digitalWrite(SIpin, LOW);
      // Each clock pulse causes a new pixel to expose its value on the two outputs:
      integrationtime = millis() - milliseconds;
      for(int i=0; i < 896; i++)
      {
          delayMicroseconds(10);// <-- We add a delay to stabilize the AO output from the sensor
          IntArray[i] = analogRead(AOpin1) / 4; //convert 1024 range to 256 range
          ClockPulse(); 
      }



      // Read and set the LED brightness
      ledbrightness = analogRead(5)/8;    //convert 1024 range to 256 range
      analogWrite(5, ledbrightness);      // Set LED brightness


      // Next, send the measurement stored in the array to host computer using serial (rs-232).
      // communication. This takes ~220 ms during whick time no clock pulses reaches the sensor. 
      // No integration is taking place during this time from the photodiodes as the integration 
      // begins first after the 18th clock pulse after a SI pulse is inserted:
      Serial.print("!"); //Every measurement output starts with an exclamation mark
      for(int i = 0; i < 895; i++)
      {
          Serial.print(IntArray[i]); Serial.print(",");
      }
      Serial.print(IntArray[895]); Serial.print("|");
      Serial.print(ledbrightness); Serial.print(",");
      Serial.print(integrationtime);
      Serial.println(""); // <-- Send a linebreak to indicate the measurement is transmitted.

      
      // Start new integration period (same structure as when stopping the integration period)
      // => Integration time is defined as the time between subsequent readings of a pixel
      digitalWrite(SIpin, HIGH);
      ClockPulse();
      digitalWrite(SIpin, LOW);
      // Each clock pulse causes a new pixel to expose its value on the two outputs:
      milliseconds = millis();  //Start time of the integration
      for(int i=0; i < 896; i++)
      {
          delayMicroseconds(10);
          IntArray[i] = analogRead(AOpin1) / 4;
          ClockPulse(); 
      }
      
      
      // Add additional integration time (without any delay it is ~42ms)
     delay(analogRead(3)/8); // Read integration delay from potentiometer
}

// This function generates an outgoing clock pulse from the Arduino digital pin 'CLKpin'. This clock
// pulse is fed into pin 3 of the linear sensor:
void ClockPulse()
{
  delayMicroseconds(1);
  digitalWrite(CLKpin, HIGH);
  digitalWrite(CLKpin, LOW);
}


