// Parallel read of the linear sensor array TSL1402R (= the sensor with 256 photodiodes)
// modified to work with TSL2014 896 channel array by B. Leverington
//-------------------------------------------------------------------------------------

// Define various ADC prescaler:
const unsigned char PS_32 = (1 << ADPS2) | (1 << ADPS0);
const unsigned char PS_128 = (1 << ADPS2) | (1 << ADPS1) | (1 << ADPS0);
int CLKpin = 4;    // <-- Arduino pin delivering the clock pulses to pin 3 (CLK) of the TSL1402R / pin 6 of TSL2014
int SIpin = 6;     // <-- Arduino pin delivering the SI (serial-input) pulse to pin 2 of the TSL1402R / pin 2 of TSL2014
int AOpin1 = 1;    // <-- Arduino pin connected to pin 4 (analog output 1)of the TSL1402R / pin 3 of TSL2014
int AOpin2 = 2;    // <-- Arduino pin connected to pin 8 (analog output 2)of the TSL1402R / pin 8 of TSL2014 (separate pins for parallel; currently read in seriel)
uint8_t IntArray[897]; // <-- the array where the readout of the photodiodes is stored, as integers (not enough memory for longer values)
int val;

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
  
      analogWrite(5, analogRead(5)/4); //led brightness coupled to potentiometer
      //   analogWrite(5, 40); // fixed LED brightness
     
      // Stop the ongoing integration of light quanta from each photodiode by clocking in a SI pulse 
      // into the sensors register:
      digitalWrite(SIpin, HIGH);
      ClockPulse();
      digitalWrite(SIpin, LOW);
      IntArray[0]=0;  
      // Next, read all 896 pixels in parallell. Store the result in the array. Each clock pulse 
      // causes a new pixel to expose its value on the two outputs:
      for(int i=1; i < 897; i++)
      {
          delayMicroseconds(20);// <-- We add a delay to stabilize the AO output from the sensor
          IntArray[i] = analogRead(AOpin1) / 4; //convert 1024 range to 256 range
         // IntArray[i+128] = analogRead(AOpin2); // for reading both arrays in parallel
          ClockPulse(); 
      }

      // Next, stop the ongoing integration of light quanta from each photodiode by clocking in a
      // SI pulse:
      digitalWrite(SIpin, HIGH);
      ClockPulse(); 
      digitalWrite(SIpin, LOW);

      // Next, send the measurement stored in the array to host computer using serial (rs-232).
      // communication. This takes ~80 ms during whick time no clock pulses reaches the sensor. 
      // No integration is taking place during this time from the photodiodes as the integration 
      // begins first after the 18th clock pulse after a SI pulse is inserted:
      for(int i = 0; i < 896; i++)
      {
          Serial.print(IntArray[i]); Serial.print(",");
      }
           Serial.print(IntArray[896]);  
      Serial.println(""); // <-- Send a linebreak to indicate the measurement is transmitted.

      // Next, a new measuring cycle is starting once 18 clock pulses have passed. At  
      // that time, the photodiodes are once again active. We clock out the SI pulse through
      // the 896 bit register in order to be ready to halt the ongoing measurement at our will
      // (by clocking in a new SI pulse):
      for(int i = 0; i < 900; i++)
      {
          if(i==18)
          {
              // Now the photodiodes goes active..
              // An external trigger can be placed here
          }
          ClockPulse(); 
      }    

      // The integration time of the current program / measurement cycle is ~3ms. If a larger time
      // of integration is wanted, uncomment the next line:
     // delay(100);// <-- Add 100 ms integration time
       val = int(analogRead(3)/5);
       delay(val); //integration time from potentiometer
}

// This function generates an outgoing clock pulse from the Arduino digital pin 'CLKpin'. This clock
// pulse is fed into pin 3 of the linear sensor:
void ClockPulse()
{
  delayMicroseconds(1);
  digitalWrite(CLKpin, HIGH);
  digitalWrite(CLKpin, LOW);
}


