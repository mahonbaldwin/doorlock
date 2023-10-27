# Doorlock

This is a lock for a sliding door using a dowel and a pair of servos.

## Supplies
- Raspberry Pi Pico W
- 2 servos [link](https://amzn.to/43zHBip)
- 2 longer servo horns [link](https://amzn.to/3mxZw8z)
- LCD display [link](https://amzn.to/40cQFIQ)
- dowel
- wire
- 4 buttons
  - lock
  - unlock
  - toggle display
- magnetic proximity switch [link](https://amzn.to/3AivLMx).
- nfc tokens [link](https://amzn.to/3zZ2juD)

## Dependencies
- [Micropython](https://pypi.org/project/micropython-phew/)
  - Install to Pico's `/lib` folder. (Tested with version `0.0.3`.)
  - i2c_lcd.py and lcd_api.py in root. (from https://peppe8o.com/using-i2c-lcd-display-with-raspberry-pi-pico-and-micropython/)

## Wiring
- Magnetic proximity switch
  - N.C. to GP18
  - Com. to ground
- Both servos
  - black to ground
  - red to power
  - white to GP1
- unlock button
  - ground
  - GP15
- lock button
  - ground
  - GP14
- reset button
  - ground
  - pin 30 (not GP pin)
- LCD display
  - GND to ground
  - VCC to power
  - SDA to GP10
  - SCL to GP11

## FAQ
- Why a dowel? Why not use a solenoid?
  - I wanted something that would stay locked in the event of a power outage without the associated risks. With a solenoid it would either lock by default or be unlocked by default and without power couldn't be unlocked which would be bad if there were an emergency requiring an escape.
- Can people connect to the Pico W's server and open the door without your permission?
  - Only people who have access to your LAN have access to the Pico server.

\* Note: Some of the links provided here are affiliate links, but will not affect the end price of the items.
