/*
TITLE: RP2040 HUB TEST FIRMWARE
REV: A.0
NOTES:
Inital Release 1/20/23


*/

#include <USB.h>

#define HUB_ID "0000"

#define GPU_1_D  18
#define GPU_1_U  19

#define GPU_2_D  17
#define GPU_2_U  16

#define GPU_3_D  6
#define GPU_3_U  5

#define GPU_4_D  8
#define GPU_4_U  7

#define PWR_SW_EN_1 23
#define PWR_SW_EN_2 1
#define PWR_SW_EN_3 25
#define PWR_SW_EN_4 24

#define USBPE_EN_1 9
#define USBPE_EN_2 0
#define USBPE_EN_3 10
#define USBPE_EN_4 11

#define GPIO_DWN 15
#define GPIO_UP  20

#define MAX_STR_BUFF 26
#define MAX_USB_CH 4

int GP_D[4] = {GPU_1_D, GPU_2_D, GPU_3_D, GPU_4_D};
int GP_U[4] = {GPU_1_U, GPU_2_U, GPU_3_U, GPU_4_U};
int PW_SW_EN[4] = {PWR_SW_EN_1, PWR_SW_EN_2, PWR_SW_EN_3, PWR_SW_EN_4 };
int USBPE_EN[4] = {USBPE_EN_1, USBPE_EN_2, USBPE_EN_3, USBPE_EN_4 };
//
// FORMAT: #{PWR_5V 0000},{USB_PE 0000},{GPIO_U 0000},{GPIO_D 0000}\n
// EX: #000,000,000,000
char str_rx[MAX_STR_BUFF];
volatile int rx_index = 0;
volatile int chan_index = 0;
volatile int new_command;
//
// COMMMAND SET
#define CMD_USB "USB"
#define CMD_ID_R  "ID?"
#define CMD_ID_W  "IDW"
#define CMD_GPIO_UD "GUD"

enum commands_ids {
  cmd_invalid,
  cmd_id_read,
  cmd_id_write,
  cmd_usb,
  cmd_gpio_ud,
  cmd_adc,
};
//


// USB STATE MACHINE
enum state_machine {
  ST_START,
  ST_PWR,
  ST_USB_EN,
  ST_GP_U,
  ST_GP_D,
  ST_COMPLETE,  
};
//
struct hub_settings
{
  int PWR[4];
  int USB_PE[4];
  int GPIO_U[4];
  int GPIO_D[4];
};

hub_settings hub_command;
volatile state_machine current_state = ST_START;
//
void serialEvent() 
{
  //statements
  if(rx_index > MAX_STR_BUFF - 1) rx_index = 0;
  char c = Serial.read();
  //Serial.print(char_index); Serial.print(" : ");  Serial.println(c);

  //
  switch (c) 
  {
    case '#':
    // clear string
    memcpy(str_rx, 0, MAX_STR_BUFF-1);   
    rx_index = 0;

    break;

    case '\n':
    rx_index = 0;

    //for(int j=0; j<MAX_STR_BUFF; j++) {Serial.print(j);Serial.print(':'); Serial.print(str_rx[j]); Serial.println(' ');}
    new_command = get_command();
    process_command(new_command);
  
    // clear string
    memcpy(str_rx, 0, MAX_STR_BUFF-1);   
    break;

    default:

    break; 
  }
  
  str_rx[rx_index++] = c;
}


int get_command()
{
  char char_str[3] = { str_rx[1], str_rx[2], str_rx[3] };  
  String str_command = char_str;
  #ifdef DEBUG
    Serial.print("str_command:"); Serial.println(str_command);
  #endif

  int return_val = cmd_invalid;
  
  if(str_command == CMD_ID_R)
  {
    return_val = cmd_id_read;
  }
  else if (str_command == CMD_USB)
  {
    return_val = cmd_usb;
  }
  
  else if(str_command == CMD_GPIO_UD)
  {
  return_val = cmd_gpio_ud;
  }
  else
  {
  Serial.print("#"); Serial.print(str_command); Serial.println(":INVALID");
  return_val = cmd_invalid;
  }

  return return_val;
}


void process_command(int command_code)
{
  String  return_str;
  switch (command_code)
  {
    case cmd_id_read:
    return_str = String("$:HUB:") + HUB_ID;
    Serial.println(return_str);
    break;

    case cmd_usb:
    usb_routine();
    break;
    
    case cmd_gpio_ud:
    gpio_ud_routine();
    break;
    
    default:
    break;

  }
}


void usb_routine()
{ 
  int chan_index = 0;
  current_state = ST_PWR;

  for (int char_index = 5; char_index < (MAX_STR_BUFF-1); char_index ++ )
  {
    int i = (str_rx[char_index] - 0x30);
    if(i >= 0 && i < 10)
    {
      if(current_state == ST_PWR)
      {
        hub_command.PWR[(MAX_USB_CH-1) -chan_index++] = i;
        if(chan_index >= MAX_USB_CH) {chan_index = 0; current_state = ST_USB_EN;}
      }

      else if(current_state == ST_USB_EN)
      {
        hub_command.USB_PE[(MAX_USB_CH-1)-chan_index++] = i;
        if(chan_index >= MAX_USB_CH) {chan_index = 0; current_state = ST_GP_U;}
      }

      else if(current_state == ST_GP_U)
      {
        hub_command.GPIO_U[(MAX_USB_CH-1) - chan_index++] = i;
        if(chan_index >= MAX_USB_CH) {chan_index = 0; current_state = ST_GP_D;}
      }

      else if(current_state == ST_GP_D)
      {
        hub_command.GPIO_D[(MAX_USB_CH-1) - chan_index++] = i;
        if(chan_index >= MAX_USB_CH) {chan_index = 0; current_state = ST_COMPLETE;}
      }
    }
  }

  Serial.print("$USB:");
  for(int port=0; port<4; port++)
  {
    Serial.print(hub_command.PWR[3-port]);
    digitalWrite(PW_SW_EN[port], hub_command.PWR[port] );  
  }
  Serial.print(',');

  for(int port=0; port<4; port++)
  {
    Serial.print(hub_command.USB_PE[3-port]);
    digitalWrite(USBPE_EN[port], hub_command.USB_PE[port] );  
  }
  Serial.print(',');

  for(int port=0; port<4; port++)
  {
    Serial.print(hub_command.GPIO_U[3-port]);
    digitalWrite(GP_U[port], hub_command.GPIO_U[port] );  
  }
  Serial.print(',');

  for(int port=0; port<4; port++)
  {
    Serial.print(hub_command.GPIO_D[3-port]);
    digitalWrite(GP_D[port], hub_command.GPIO_D[port]);  
  }
  Serial.print('\n');
}


void gpio_ud_routine()
{
  Serial.print("$GUD:00");
  Serial.print(digitalRead(GPIO_UP));
  Serial.println(digitalRead(GPIO_DWN));
}




// the setup routine runs once when you press reset:
void setup() {


  // set USB parameters 
  // Must *always* disconnect the USB port while doing modifications like this
  USB.disconnect();
  USB.setVIDPID(0x01ea, 0xfaaa);
  USB.setManufacturer("Olea");
  USB.setProduct("TEST_HUB");
  USB.setSerialNumber("TH-0000");
  // Everything is set, so reconnect under the new device info
  USB.connect();


  Serial.begin(115200);
  // declare pin to be an output:
  for(int port=0; port<4; port++)
  {
    pinMode(GP_D[port], OUTPUT);
    pinMode(GP_U[port], OUTPUT);
    pinMode(PW_SW_EN[port], OUTPUT);
    pinMode(USBPE_EN[port], OUTPUT);    
    
    digitalWrite(GP_D[port], 0);  
    digitalWrite(GP_U[port], 0);  
    digitalWrite(PW_SW_EN[port], 0);  
    digitalWrite(USBPE_EN[port], 0);  
  }

  pinMode(GPIO_DWN, INPUT);
  pinMode(GPIO_UP, INPUT);

}


// the loop routine runs over and over again forever:
void loop() {
  delay(1);
}





