# FT-710 CAT Operation Reference Manual

YAESU MUSEN CO., LTD.

## Overview

The CAT (Computer Aided Transceiver) System in the FT-710 transceiver provides control of frequency, VFO, memory, and other settings such as dual-channel memories and diversity reception using an external personal computer. This allows multiple control operations to be fully automated with single mouse clicks, or keystroke operations on the computer keyboard.

YAESU MUSEN does not produce CAT System operating software due to the wide variety of personal computers and operating systems in use today. However, the information provided in this chapter explains the serial data structure and opcodes used by the CAT system. This information, along with the short programming examples, is intended to help you start writing programs on your own. As you become more familiar with CAT operation, you can customize programs for your operating needs and utilize the full operating potential of this system.

## Using the USB Cable (CAT-1 / CAT-2)

The FT-710 transceiver has a built-in USB to Dual UART Bridge, allowing direct connection from the rear-panel USB jack to the USB jack of a computer without the need for an interface device, simply use a USB cable to connect to the USB jack on the computer.

To connect to a PC using a USB cable, a Virtual COM port driver must be installed on the PC. Visit the Yaesu website http://www.yaesu.com/ to download the Virtual COM port driver and Installation Manual.

PC

USB Cable

USB

```text
                                                               FT-710           USB




   How to Confirm the Installation, and the COM Port Number
   After the FT-710 and computer are connected, confirm that the virtual COM driver has been installed successfully:
```

1. Press and hold the ON/OFF switch to turn the transceiver ON.
2. Connect the transceiver and PC with a commercially available USB cable (A-B).
3. Open the “Device Manager” screen in Windows.
4. On the Device Manager screen, double-click “Port (COM & LPT)”.
“Silicon Labs Dual CP210x USB to UART Bridge : Enhanced COM Port (COM**)” “Silicon Labs Dual CP210x USB to UART Bridge : Standard COM Port (COM**)” *(The number in the “(COM**)” portion may vary from computer to computer.) The above example indicates that COM5 can be used for CAT communications (CAT-1), while COM6 can be used for TX control (PTT, CW Keying, Digital Mode Operation) or CAT communications (CAT-2). When performing software port configuration, select the COM port numbers that were confirmed using the procedure above.

If a “!” or “X” is displayed for the port on the Device Manager, uninstall and reinstall the virtual COM driver.

## CAT (Computer Aided Transceiver) Operation

The FT-710 contains two virtual COM ports, an Enhanced COM Port and a Standard COM Port. These ports offer the following functions:

- Enhanced COM Port (CAT-1): CAT Communications (Frequency and Communication Mode Settings)
- Standard COM Port (CAT-2): TX Controls (PTT control, CW Keying, Digital Mode Operation) or CAT
Communications (Frequency and Communication Mode Settings)* When performing software port configuration, select the COM port numbers that were confirmed using the procedure above, use the two confirmed COM port numbers for each software function. The frequency and communication mode and PTT control can be set from the software, and CW keying, digital communication, etc. can be performed simultaneously. *NOTE: (When using a standard COM port (CAT-2) for CAT communication (setting frequency, communication mode, etc.) and using hardware flow control by RTS or DTR, be sure to set the following menu items to “OFF” (factory default) or set to “DAKY” to disable PTT control by RTS or DTR.)

```text
     Menu Item                                  Menu Function      Available Settings (Default: Bold)
                          MODE SSB              RPTT SELECT        OFF / RTS / DTR / DAKY
                          MODE AM               RPTT SELECT        OFF / RTS / DTR / DAKY
     RADIO SETTING        MODE FM               RPTT SELECT        OFF / RTS / DTR / DAKY
                          MODE PSK/DATA         RPTT SELECT        OFF / RTS / DTR / DAKY
                          MODE RTTY             RPTT SELECT        OFF / RTS / DTR / DAKY
                                                RPTT SELECT        OFF / RTS / DTR / DAKY
     CW SETTING           MODE CW
                                                PC KEYING          OFF / RTS / DTR / DAKY
     PRESET               PRESET1 - 5           RPTT SELECT        OFF / RTS / DTR / DAKY
```

- If a transceiver with a different serial number is connected and turned on, different COM port numbers
will be assigned to it, making it possible to perform individual COM port configurations for separate transceivers.

- When using the USB cable for TX control, the transceiver may switch to the transmit mode when the
computer is started.

- Always close the application on the computer before disconnecting the USB cable.
## Using the RS-232C (CAT-3)

The TUNER/LINEAR jack on the rear panel can be used for CAT communication (5V TTL level serial communication). Set to “CAT-3” in the setting menu [OPERATION SETTING] → [GENERAL] → [TUN/LIN PORT SELECT]. (Factory setting: EXT-TUNER)

- Since the serial communication of this jack is 5V TTL level, it cannot be directly connected to the RS-232C
terminal of the PC.

- The connection cable must be prepared by yourself using the optional band data cable CT-58
(mini DIN 8-pin to DIN 8-pin).

- CAT communication cannot be used simultaneously with an external antenna tuner or linear amplifier.
TUNER/LINEAR Jack

```text
                                                          ⑦
                                                      ⑧         ⑥

                                             ⑤ RX D                 ③ GND
                                              ④ TX D
                                                    ②           ① +13V OUT

                                               (as viewed from rear panel)

          Pin No.   Pin Name       I/O                                       Function
                     +13V          –                          13 VDC output linked to radio ON
                      N/A          –                                            –
                     GND           –                                   Signal Ground
                     TXD        Output       Outputs the Serial Data from the transceiver to the PC (5V TTL)
                     RXD         Input       Inputs the Serial Data from the PC to the transceiver (5V TTL)
                      N/A          –                                            –
                      N/A          –                                            –
                      N/A          –                                            –
```

## Communication Parameters

- Asynchronous communication
- Baud rate: 38400bps* (CAT-1, CAT-3 terminals) or 4800bps* (CAT-2 terminal)
- Start bit:  1
- Data bits: 8
- Stop bits: 1 or 2* (CAT-2: 1 (Fixed))
- Paritybits: None
*(Factory default) CAT communication settings can be changed using the following menu items.

```text
 Menu Item                                Menu Function                      Available Settings (Default: Bold)
                                          CAT-1 RATE                         4800 / 9600 / 19200 / 38400 / 115200 (bps)
                                          CAT-1 TIME OUT TIMER               10 / 100 / 1000 / 3000 (msec)
                                          CAT-1 CAT-3 STOP BIT               1bit / 2bit
 OPERATION SETTING        GENERAL         CAT-2 RATE                         4800 / 9600 / 19200 / 38400 / 115200 (bps)
                                          CAT-2 TIME OUT TIMER               10 / 100 / 1000 / 3000 (msec)
                                          CAT-3 RATE                         4800 / 9600 / 19200 / 38400 / 115200 (bps)
                                          CAT-3 TIME OUT TIMER               10 / 100 / 1000 / 3000 (msec)




                                         Control Command
```

A computer control command is composed of an alphabetical command, various parameters, and the terminator that signals the end of the control command. Example: Set the VFO-A frequency to 14.250000 MHz.

```text
      FA           014250000 ;
                           
      Command      Parameter Terminator
```

There are three commands for the FT-710 as shown below:

```text
   Set command: Set a particular condition        (to the FT-710)
   Read command: Reads an answer		                (from the FT-710)
   Answer command: Transmits a condition          (from the FT-710)
```

For example, note the following case of the FA command (Set the VFO-A frequency):  To set the VFO-A frequency to 14.250000 MHz, the following command is sent from the computer to the trans- ceiver: “FA014250000;” (Set command)  To read the VFO-A frequency, the following command is sent from the computer to the transceiver: “FA;” (Read command)  When the Read command above has been sent, the following command is returned to the computer: “FA014250000;” (Answer command)

## Alphabetical Commands

A command consists of 2 alphabetical characters. You may use either lower or upper case characters. The commands available for this transceiver are listed in the “PC Control Command Tables” on the following pages.

## Parameters

Parameters are used to specify information necessary to implement the desired command. The parameters to be used for each command are predetermined. The number of digits assigned to each param- eter is also predetermined. Refer to the “Control Command List” and the “Control Command Tables” to configure the appropriate parameters. When configuring parameters, be careful not to make the following mistakes. For example, when the correct parameter is “IS00+1000” (IF SHIFT): IS001000; Not enough parameters specified (No direction (+) given for the IF shift) IS00+100; Not enough digits (Only three frequency digits given) IS00_+_1000; Unnecessary characters between parameters IS00+10000; Too many digits (Five frequency digits given) Note: If a particular parameter is not applicable to the FT-710, the parameter digits should be filled using any character except the ASCII control codes (00 to 1Fh) and the terminator (;).

## Terminator

To signal the end of a command, it is necessary to use a semicolon (;). The digit where this special character must appear differs depending on the command used.

CAT Control Command List

```text
Command           Function       Set Read Ans.   AI       Command            Function         Set Read Ans.   AI
  AB      VFO-A TO VFO-B         O    X    X     X          ML      MONITOR LEVEL             O    O    O     O

  AC      ANTENNA TUNER          O    O    O     O          MR      MEMORY READ               X    O    O     X
          CONTROL
                                                            MS      METER SW                  O    O    O     O
  AG      AF GAIN                O    O    O     O
                                                            MT      MEMORY CHANNEL            O    O    O     X
  AI      AUTO INFORMATION       O    O    O     X                  WRITE/TAG
  AM      VFO-A TO MEMORY        O    X    X     X          MW      MEMORY WRITE              O    X    X     X
          CHANNEL
                                                            MX      MOX SET                   O    O    O     O
  AO      AMC OUTPUT LEVEL       O    O    O     O
                                                            NA      NARROW                    O    O    O     O
  AS      AESS                   O    O    O     X
                                                            NB      NOISE BLANKER             O    O    O     O
  AV      ANTI VOX LEVEL         O    O    O     O
                                                            NL      NOISE BLANKER LEVEL       O    O    O     O
  BA      VFO-B TO VFO-A         O    X    X     X
                                                            NR      NOISE REDUCTION (DNR)     O    O    O     O
  BC      AUTO NOTCH (DNF)       O    O    O     O
                                                            OI      OPPOSITE BAND (VFO-B)     X    O    O     O
  BD      BAND DOWN              O    X    X     X                  INFORMATION
  BI      BREAK-IN               O    O    O     O          OS      OFFSET (Repeater Shift)   O    O    O     O

  BM      VFO-B TO MEMORY        O    X    X     X          PA      PRE-AMP (IPO)             O    O    O     O
          CHANNEL
                                                            PB      PLAY BACK                 O    O    O     X
  BP      MANUAL NOTCH           O    O    O     O
                                                            PC      POWER CONTROL             O    O    O     O
  BS      BAND SELECT            O    X    X     X
                                                            PL      SPEECH PROCESSOR          O    O    O     O
  BU      BAND UP                O    X    X     X                  LEVEL
  CF      CLAR (Clarifier)       O    O    O     O          PR      SPEECH PROCESSOR          O    O    O     O
  CH      CHANNEL UP/DOWN        O    X    X     X          PS      POWER SWITCH              O    O    O     X
  CN      CTCSS NUMBER           O    O    O     O          QI      QMB STORE                 O    X    X     X
  CO      CONTOUR/APF            O    O    O     O          QR      QMB RECALL                O    X    X     X
  CS      CW SPOT                O    O    O     O          RA      RF ATTENUATOR             O    O    O     O
  CT      CTCSS                  O    O    O     O          RG      RF GAIN                   O    O    O     O

  DA      LCD CONTRAST/          O    O    O     X          RI      RADIO INFORMATION         X    O    O     O
          DIMMER
                                                            RL      NOISE REDUCTION           O    O    O     O
  DN      DOWN                   O    X    X     X                  (DNR) LEVEL
  DT      DATE AND TIME          O    O    O     X          RM      READ METER                X    O    O     O
  EX      MENU                   O    O    O     O          SC      SCAN                      O    O    O     O
  FA      FREQUENCY VFO-A        O    O    O     O          SD      SEMI BREAK-IN DELAY       O    O    O     O
                                                                    TIME
  FB      FREQUENCY VFO-B        O    O    O     O
                                                            SF      SUB DIAL                  O    O    O     O
  FN      FINE TUNING            O    O    O     O
                                                            SH      WIDTH                     O    O    O     O
  FT      FUNCTION TX            O    O    O     O
                                                            SM      S METER                   X    O    O     X
  GP      GP OUT A/B/C/D         O    O    O     X
                                                            SQ      SQUELCH LEVEL             O    O    O     O
  GT      AGC FUNCTION           O    O    O     O
                                                            SS      SPECTRUM SCOPE            O    O    O     O
  ID      IDENTIFICATION         X    O    O     X
                                                            ST      SPLIT                     O    O    O     O
  IF      INFORMATION (VFO-A)    X    O    O     O
                                                            SV      SWAP VFO                  O    X    X     X
  IS      IF SHIFT               O    O    O     O
                                                            TS      TXW                       O    O    O     O
  KM      KEYER MEMORY           O    O    O     X
                                                            TX      TX SET                    O    O    O     O
  KP      KEY PITCH              O    O    O     O
                                                            UP      UP                        O    X    X     X
  KR      KEYER                  O    O    O     O
                                                            VD      VOX DELAY TIME            O    O    O     O
  KS      KEY SPEED              O    O    O     O
                                                            VE      FIRMWARE VERSION          X    O    O     X
  KY      CW KEYING              O    X    X     X
                                                            VG      VOX GAIN                  O    O    O     O
  LK      LOCK                   O    O    O     O
                                                            VM      [V/M] KEY FUNCTION        O    X    X     X
  LM      LOAD MESSAGE           O    O    O     X
                                                            VS      VFO SELECT                O    O    O     O
  MA      MEMORY CHANNEL TO      O    X    X     X
          VFO-A                                             VX      VOX                       O    O    O     O

  MB      MEMORY CHANNEL TO      O    X    X     X          ZI      ZERO IN                   O    X    X     X
          VFO-B
  MC      MEMORY CHANNEL         O    O    O     X
  MD      MODE                   O    O    O     O
  MG      MIC GAIN               O    O    O     O



```

### AB — VFO-A TO VFO-B

```text
         1   2     3   4   5   6   7   8   9   10
Set
         A   B     ;
         1   2     3   4   5   6   7   8   9   10
Read
         1   2     3   4   5   6   7   8   9   10
Answer


```

### AC — ANTENNA TUNER CONTROL

```text
                                                    P1 0: (Fixed)
         1   2     3   4   5   6   7   8   9   10
                                                    P2 0: Internal or External Antenna Tuner
Set                                                    1: -
         A   C   P1 P2 P3      ;                       2: ATAS
                                                    P3 P2=0 (Antenna Tuner):
         1   2     3   4   5   6   7   8   9   10   		 0: Tuner “OFF” (Tuning Stop)
Read                                                		 1: Tuner “ON”
         A   C     ;                                		 2: -
                                                    		 3: Tuning Start
                                                       P2=2 (ATAS):
         1   2     3   4   5   6   7   8   9   10
                                                    		 0: Tuning Stop
Answer                                              		 1: Tuning frequency up (50 msec)
         A   C   P1 P2 P3      ;                    		 2: Tuning frequency down (50 msec)
                                                    		 3: Tuning Start


```

### AG — AF GAIN

```text
         1   2     3   4   5   6   7   8   9   10   P1 0: (Fixed)
Set
         A   G   P1 P2 P2 P2       ;                P2 000 - 255
         1   2     3   4   5   6   7   8   9   10
Read
         A   G   P1    ;
         1   2     3   4   5   6   7   8   9   10
Answer
         A   G   P1 P2 P2 P2       ;


```

### AI — AUTO INFORMATION

```text
         1   2     3   4   5   6   7   8   9   10   P1 0: Auto Information “OFF”
Set                                                    1: Auto Information “ON”
         A   I   P1    ;
         1   2     3   4   5   6   7   8   9   10   NOTES:
Read                                                 • When the status of the radio changes, the Read value of the AI applicable command (see
         A   I     ;                                   “CAT Control Command List” (page 5)) is automatically sent to the PC.
         1   2     3   4   5   6   7   8   9   10    • Set ON/OFF for each CAT-1, CAT-2, and CAT-3.
Answer                                               • This parameter is set to “0” (OFF) automatically when the transceiver is turned “OFF”.
         A   I   P1    ;


```

### AM — VFO-A TO MEMORY CHANNEL

```text
         1   2     3   4   5   6   7   8   9   10
Set
         A   M     ;
         1   2     3   4   5   6   7   8   9   10
Read
         1   2     3   4   5   6   7   8   9   10
Answer


```

### AO — AMC OUTPUT LEVEL

```text
         1   2     3   4   5   6   7   8   9   10   P1 001-100: AMC OUTPUT LEVEL
Set
         A   O   P1 P1 P1      ;
         1   2     3   4   5   6   7   8   9   10
Read
         A   O     ;
         1   2     3   4   5   6   7   8   9   10
Answer
         A   O   P1 P1 P1      ;


```

### AS — AESS

```text
         1   2     3   4   5   6   7   8   9   10   P1 1: AESS LEVEL
Set                                                    2: AESS-CF (Cut off frquecny)
         A   S   P1 P2 P2 P2       ;
                                                    P2 P1=1 (AESS LEVEL):
         1   2     3   4   5   6   7   8   9   10
Read                                                		 P2: 000 - 100
         A   S   P1    ;                               P1=2 (AESS-CF (Cut off frquecny)):
         1   2     3   4   5   6   7   8   9   10   		 001: 700Hz
Answer                                              		 002: 1000Hz
         A   S   P1 P2 P2 P2       ;




```

### AV — ANTI VOX LEVEL

```text
         1   2   3    4   5   6   7   8   9   10   P1 001-100: ANTI VOX LEVEL
Set
         A   V   P1 P1 P1     ;
         1   2   3    4   5   6   7   8   9   10
Read
         A   V   ;
         1   2   3    4   5   6   7   8   9   10
Answer
         A   V   P1 P1 P1     ;


```

### BA — VFO-B TO VFO-A

```text
         1   2   3    4   5   6   7   8   9   10
Set
         B   A   ;
         1   2   3    4   5   6   7   8   9   10
Read
         1   2   3    4   5   6   7   8   9   10
Answer


```

### BC — AUTO NOTCH

```text
         1   2   3    4   5   6   7   8   9   10   P1 0: (Fixed)
Set
         B   C   P1 P2    ;                        P2 0: Auto Notch “OFF”
         1   2   3    4   5   6   7   8   9   10      1: Auto Notch “ON”
Read
         B   C   P1   ;
         1   2   3    4   5   6   7   8   9   10
Answer
         B   C   P1 P2    ;


```

### BD — BAND DOWN

```text
         1   2   3    4   5   6   7   8   9   10   P1 0: MAIN BAND
Set
         B   D   P1   ;                               1: SUB BAND
         1   2   3    4   5   6   7   8   9   10
Read
         1   2   3    4   5   6   7   8   9   10
Answer


```

### BI — BREAK-IN

```text
         1   2   3    4   5   6   7   8   9   10   P1 0: Break-in “OFF”
Set
         B   I   P1   ;                               1: Break-in “ON”
         1   2   3    4   5   6   7   8   9   10
Read
         B   I   ;
         1   2   3    4   5   6   7   8   9   10
Answer
         B   I   P1   ;


```

### BM — VFO-B TO MEMORY CHANNEL

```text
         1   2   3    4   5   6   7   8   9   10
Set
         B   M   ;
         1   2   3    4   5   6   7   8   9   10
Read
         1   2   3    4   5   6   7   8   9   10
Answer


```

### BP — MANUAL NOTCH

```text
         1   2   3    4   5   6   7   8   9   10   P1 0: (Fixed)
Set                                                P2 0: Manual NOTCH “ON/OFF”
         B   P   P1 P2 P3 P3 P3       ;
                                                      1: Manual NOTCH Frequency
         1   2   3    4   5   6   7   8   9   10   P3 P2=0
Read                                               		     000: “OFF”
         B   P   P1 P2    ;
                                                          001: “ON”
         1   2   3    4   5   6   7   8   9   10
                                                      P2=1
Answer
         B   P   P1 P2 P3 P3 P3       ;            		 001 - 320 (NOTCH Frequency : x 10 Hz )


```

### BS — BAND SELECT

```text
         1   2   3    4   5   6   7   8   9   10   P1 00: 1.8 MHz         06: 18 MHz
Set
         B   S   P1 P1    ;                           01: 3.5 MHz         07: 21 MHz
         1   2   3    4   5   6   7   8   9   10      02: 5 MHz           08: 24.5 MHz
Read                                                  03: 7 MHz           09: 28 MHz
                                                      04: 10 MHz          10: 50 MHz
         1   2   3    4   5   6   7   8   9   10
Answer                                                05: 14 MHz          11: 70 MHz/GEN




```

### BU — BAND UP

```text
         1     2   3    4    5     6   7    8     9     10   P1 0: MAIN BAND
Set
         B     U   P1   ;                                       1: SUB BAND
         1     2   3    4    5     6   7    8     9     10
Read
         1     2   3    4    5     6   7    8     9     10
Answer


```

### CF — CLAR ON/OFF

```text
         1     2   3    4    5     6   7    8     9     10   11   P1 0: MAIN BAND                   P3=1 (CLAR Frequency):
Set                                                                  1: SUB BAND                      P4     +/-
         C     F   P1 P2 P3 P4 P5 P6 P7 P8                    ;   P2 0: (Fixed)                       P5-P8 0000 - 9999 Hz
                                                                  P3 0: CLAR Setting
         1     2   3    4    5     6   7    8     9     10   11      1: CLAR Frequency
Read                                                              P3=0 (CLAR Setting):
         C     F   P1 P2 P3        ;                                P4       0: RX CLAR OFF
                                                                  			        1: RX CLAR ON
         1     2   3    4    5     6   7    8     9     10   11     P5       0: TX CLAR OFF
Answer                                                            			        1: TX CLAR ON
         C     F   P1 P2 P3 P4 P5 P6 P7 P8                    ;     P6-P8 0: (Fixed)



```

### CH — CHANNEL UP/DOWN

```text
         1     2   3    4    5     6   7    8     9     10   P1 0: Memory Channel “UP”
Set
         C     H   P1   ;                                       1: Memory Channel “DOWN”
         1     2   3    4    5     6   7    8     9     10
Read
         1     2   3    4    5     6   7    8     9     10
Answer


```

### CN — CTCSS TONE FREQUENCY

```text
         1     2   3    4    5     6   7    8     9     10   P1 0: MAIN BAND
Set
         C     N   P1 P2 P3 P3 P3           ;                   1: SUB BAND
         1     2   3    4    5     6   7    8     9     10   P2 0: (Fixed)
Read                                                         P3 000 - 049: Tone Frequency Number (See Table 1)
         C     N   P1 P2     ;
         1     2   3    4    5     6   7    8     9     10
Answer
         C     N   P1 P2 P3 P3 P3           ;
```

Table 1 (CTCSS Tone Chart)

```text
             000   67.0 Hz       009   91.5 Hz        018    123.0 Hz       027   162.2 Hz    036     189.9 Hz   045    229.1 Hz
             001   69.3 Hz       010   94.8 Hz        019    127.3 Hz       028   165.5 Hz    037     192.8 Hz   046    233.6 Hz
             002   71.9 Hz       011   97.4 Hz        020    131.8 Hz       029   167.9 Hz    038     196.6 Hz   047    241.8 Hz
             003   74.4 Hz       012   100.0 Hz       021    136.5 Hz       030   171.3 Hz    039     199.5 Hz   048    250.3 Hz
             004   77.0 Hz       013   103.5 Hz       022    141.3 Hz       031   173.8 Hz    040     203.5 Hz   049    254.1 Hz
             005   79.7 Hz       014   107.2 Hz       023    146.2 Hz       032   177.3 Hz    041     206.5 Hz    -         -
             006   82.5 Hz       015   110.9 Hz       024    151.4 Hz       033   179.9 Hz    042     210.7 Hz    -         -
             007   85.4 Hz       016   114.8 Hz       025    156.7 Hz       034   183.5 Hz    043     218.1 Hz    -         -
             008   88.5 Hz       017   118.8 Hz       026    159.8 Hz       035   186.2 Hz    044     225.7 Hz    -         -


```

### CO — CONTOUR

```text
         1     2   3    4    5     6   7    8     9     10   P1 0: (Fixed)          P3 P2=0 0000: CONTOUR “OFF”
Set                                                          P2 0: CONTOUR “ON/OFF”			      0001: CONTOUR “ON”
         C     O   P1 P2 P3 P3 P3 P3              ;
                                                                1: CONTOUR FREQ		      P2=1 0010 - 3200
         1     2   3    4    5     6   7    8     9     10
Read                                                            2: APF “ON/OFF”			          (CONTOUR Frequency:10 - 3200Hz)
         C     O   P1 P2     ;                                  3: APF FREQ		          P2=2 0000: APF “OFF”
         1     2   3    4    5     6   7    8     9     10   				 0001: APF “ON”
Answer                                                       			P2=3 0000 - 0050 (APF Frequency: -250 - 250 Hz )
         C     O   P1 P2 P3 P3 P3 P3              ;


```

### CS — CW SPOT

```text
         1     2   3    4    5     6   7    8     9     10   P1 0: CW SPOT “OFF”
Set
         C     S   P1   ;                                       1: CW SPOT “ON”
         1     2   3    4    5     6   7    8     9     10
Read
         C     S   ;
         1     2   3    4    5     6   7    8     9     10
Answer
         C     S   P1   ;




```

### CT — CTCSS

```text
         1   2    3   4   5   6   7   8   9     10   P1 0: MAIN BAND
Set
         C   T   P1 P2    ;                             1: SUB BAND
         1   2    3   4   5   6   7   8   9     10   P2 0: CTCSS “OFF”
Read                                                    1: CTCSS ENC “ON” / DEC “ON”
         C   T   P1   ;
                                                        2: CTCSS ENC “ON” / DEC “OFF”
         1   2    3   4   5   6   7   8   9     10
Answer
         C   T   P1 P2    ;


```

### DA — DIMMER

```text
         1   2    3   4   5   6   7   8   9     10   11   P1   00: (Fixed)
Set
         D   A   P1 P1 P2 P2 P3 P3 P4 P4              ;   P2   00 - 20: TFT Display Contrast
         1   2    3   4   5   6   7   8   9     10   11   P3   00 - 20: TFT Display Brightness Level
Read                                                      P4   00 - 20: LED Indicators Brightness Level
         D   A    ;
         1   2    3   4   5   6   7   8   9     10   11
Answer
         D   A   P1 P1 P2 P2 P3 P3 P4 P4              ;


```

### DN — MIC DOWN

```text
         1   2    3   4   5   6   7   8   9     10
Set
         D   N    ;
         1   2    3   4   5   6   7   8   9     10
Read
         1   2    3   4   5   6   7   8   9     10
Answer


```

### DT — DATE AND TIME

```text
         1   2    3   4   5   6   7   ~   n-1   n    P1 0: Date
Set
         D   T   P1 P2 P2 P2 P2       ~   P2    ;       1: Time (UTC)
         1   2    3   4   5   6   7   8   9     10   P2 P1=0     yyyymmdd (Year/Month/Date)
Read                                                    P1=1     hhmmss (Hour/Minute/Second, 24 hour time system)
         D   T   P1   ;
         1   2    3   4   5   6   7   ~   n-1   n
Answer
         D   T   P1 P2 P2 P2 P2       ~   P2    ;


```

### EX — MENU

```text
         1   2    3   4   5   6   7   8   9     ~    nn   **   P1   : 01 - 04, 05
Set
         E   X   P1 P1 P2 P2 P3 P3 P4           ~    P4    ;   P2   : 01 - 05
         1   2    3   4   5   6   7   8   9     10   nn   **   P3   : 01 - 26
Read                                                           P4   : Parameter (See Table 2)
         E   X   P1 P1 P2 P2 P3 P3         ;
         1   2    3   4   5   6   7   8   9     ~    nn   **
Answer
         E   X   P1 P1 P2 P2 P3 P3 P4           ~    P4    ;
```

Table 2 (MENU Chart)

```text
      P1                P2          P3          Function                                                   P4                                         Digits
                                    01   AF TREBLE GAIN         -20 - -00 (or +00) - +10 (P4 = -20 - -00 or +00 - +10)                                  3
                                    02   AF MIDDLE TONE GAIN    -20 - -00 (or +00) - +10 (P4 = -20 - -00 or +00 - +10)                                  3
                                    03   AF BASS GAIN           -20 - -00 (or +00) - +10 (P4 = -20 - -00 or +00 - +10)                                  3
                                    04   AGC FAST DELAY         20 - 4000 msec (P4= 0020 - 4000, 20 msec/step)                                          4
                                    05   AGC MID DELAY          20 - 4000 msec (P4= 0020 - 4000, 20 msec/step)                                          4
                                    06   AGC SLOW DELAY         20 - 4000 msec (P4= 0020 - 4000, 20 msec/step)                                          4
                                    07   LCUT FREQ              00: OFF 01: 100 Hz - 19: 1000 Hz (50 Hz steps)                                          2
                                    08   LCUT SLOPE             0: 6 dB/oct 1: 18 dB/oct                                                                1
                                    09   HCUT FREQ              00: OFF 01: 700 Hz - 67: 4000 Hz (50 Hz steps)                                          2
                                    10   HCUT SLOPE             0: 6 dB/oct 1: 18 dB/oct                                                                1
                    (MODE SSB)      11   USB OUT LEVEL          000 - 100                                                                               3
                                    12   REAR OUT LEVEL         000 - 100                                                                               3
                                    13   TX BPF SEL             0: 50 - 3050 1: 100 - 2900 2: 200 - 2800 3: 300 - 2700           4: 400 - 2600 (Hz)     1
                                    14   MOD SOURCE             0: MIC 1: USB 2: REAR (RTTY/DATA Jack) 3: AUTO                                          1
                                    15   USB MOD GAIN           000 - 100                                                                               3
                                    16   REAR MOD GAIN          000 - 100                                                                               3
                                    17   RPTT SELECT            0: OFF 1: RTS 2: DTR 3: DAKY                                                            1
                                                                00: 300     01: 400    02: 600   03: 850     04: 1100 05: 1200   06: 1500 07: 1650
                                    18   NAR WIDTH              08: 1800 09: 1950 10: 2100 11: 2250 12: 2400 13: 2450            14: 2500 15: 2600      2
                                                                16: 2700 17: 2800 18: 2900 19: 3000 20: 3200 21: 3500            22: 4000 (Hz)
                                    19   CW AUTO MODE           0: OFF 1: 50MHz 2: ON                                                                   1
                                    01   AF TREBLE GAIN         -20 - -00 (or +00) - +10 (P4 = -20 - -00 or +00 - +10)                                  3
                                    02   AF MIDDLE TONE GAIN    -20 - -00 (or +00) - +10 (P4 = -20 - -00 or +00 - +10)                                  3
                                    03   AF BASS GAIN           -20 - -00 (or +00) - +10 (P4 = -20 - -00 or +00 - +10)                                  3
                                    04   AGC FAST DELAY         20 - 4000 msec (P4= 0020 - 4000, 20 msec/step)                                          4
                                    05   AGC MID DELAY          20 - 4000 msec (P4= 0020 - 4000, 20 msec/step)                                          4
                                    06   AGC SLOW DELAY         20 - 4000 msec (P4= 0020 - 4000, 20 msec/step)                                          4
                                    07   LCUT FREQ              00: OFF 01: 100 Hz - 19: 1000 Hz (50 Hz steps)                                          2
                                    08   LCUT SLOPE             0: 6 dB/oct 1: 18 dB/oct                                                                1
                                    09   HCUT FREQ              00: OFF 01: 700 Hz - 67: 4000 Hz (50 Hz steps)                                          2
                    (MODE AM)
                                    10   HCUT SLOPE             0: 6 dB/oct 1: 18 dB/oct                                                                1
                                    11   USB OUT LEVEL          000 - 100                                                                               3
                                    12   REAR OUT LEVEL         000 - 100                                                                               3
                                    13   TX BPF SEL             0: 50 - 3050 1: 100 - 2900 2: 200 - 2800 3: 300 - 2700           4: 400 - 2600          1
                                    14   MOD SOURCE             0: MIC 1: USB 2: REAR (RTTY/DATA Jack) 3: AUTO                                          1
                                    15   USB MOD GAIN           000 - 100                                                                               3
                                    16   REAR MOD GAIN          000 - 100                                                                               3
                                    17   RPTT SELECT            0: OFF 1: RTS 2: DTR 3: DAKY (RTTY/DATA Jack)                                           1
                                    01   AF TREBLE GAIN         -20 - -00 (or +00) - +10 (P4 = -20 - -00 or +00 - +10)                                  3
                                    02   AF MIDDLE TONE GAIN    -20 - -00 (or +00) - +10 (P4 = -20 - -00 or +00 - +10)                                  3
                                    03   AF BASS GAIN           -20 - -00 (or +00) - +10 (P4 = -20 - -00 or +00 - +10)                                  3
```

(RADIO SETTING)

```text
                                    04   AGC FAST DELAY         20 - 4000 msec (P4= 0020 - 4000, 20 msec/step)                                          4
                                    05   AGC MID DELAY          20 - 4000 msec (P4= 0020 - 4000, 20 msec/step)                                          4
                                    06   AGC SLOW DELAY         20 - 4000 msec (P4= 0020 - 4000, 20 msec/step)                                          4
                                    07   LCUT FREQ              00: OFF 01: 100 Hz - 19: 1000 Hz (50 Hz steps)                                          2
                                    08   LCUT SLOPE             0: 6 dB/oct 1: 18 dB/oct                                                                1
                                    09   HCUT FREQ              00: OFF 01: 700 Hz - 67: 4000 Hz (50 Hz steps)                                          2
                                    10   HCUT SLOPE             0: 6 dB/oct 1: 18 dB/oct                                                                1
                                    11   USB OUT LEVEL          000 - 100                                                                               3
                    (MODE FM)
                                    12   REAR OUT LEVEL         000 - 100                                                                               3
                                    13   MOD SOURCE             0: MIC 1: USB 2: REAR (RTTY/DATA Jack) 3: AUTO                                          1
                                    14   USB MOD GAIN           000 - 100                                                                               3
                                    15   REAR MOD GAIN          000 - 100                                                                               3
                                    16   RPTT SELECT            0: OFF 1: RTS 2: DTR 3: DAKY (RTTY/DATA Jack)                                           1
                                    17   RPT SHIFT              0: - 1: SIMPLEX 2: +                                                                    1
                                    18   RPT SHIFT(28MHz)       0 - 1000 kHz (P4 = 0000 - 1000, 10 kHz/step)                                            4
                                    19   RPT SHIFT(50MHz)       0 - 4000 kHz (P4 = 0000 - 4000, 10 kHz/step)                                            4
                                    20   ENC/DEC                0: OFF 1: ENC 2: TSQ                                                                    1
                                    21   TONE FREQ              00: 67.0 - 49: 254.1Hz                                                                  2
                                    01   AF TREBLE GAIN         -20 - -00 (or +00) - +10 (P4 = -20 - -00 or +00 - +10)                                  3
                                    02   AF MIDDLE TONE GAIN    -20 - -00 (or +00) - +10 (P4 = -20 - -00 or +00 - +10)                                  3
                                    03   AF BASS GAIN           -20 - -00 (or +00) - +10 (P4 = -20 - -00 or +00 - +10)                                  3
                                    04   AGC FAST DELAY         20 - 4000 msec (P4= 0020 - 4000, 20 msec/step)                                          4
                                    05   AGC MID DELAY          20 - 4000 msec (P4= 0020 - 4000, 20 msec/step)                                          4
                                    06   AGC SLOW DELAY         20 - 4000 msec (P4= 0020 - 4000, 20 msec/step)                                          4
                                    07   LCUT FREQ              00: OFF 01: 100 Hz - 19: 1000 Hz (50 Hz steps)                                          2
                                    08   LCUT SLOPE             0: 6 dB/oct 1: 18 dB/oct                                                                1
                                    09   HCUT FREQ              00: OFF 01: 700 Hz - 67: 4000 Hz (50 Hz steps)                                          2
                                    10   HCUT SLOPE             0: 6 dB/oct 1: 18 dB/oct                                                                1
                        04          11   USB OUT LEVEL          000 - 100                                                                               3
                  (MODE PSK/DATA)   12   REAR OUT LEVEL         000 - 100                                                                               3
                                    13   TX BPF SEL             0: 50 - 3050 1: 100 - 2900 2: 200 - 2800 3: 300 - 2700           4: 400 - 2600          1
                                    14   MOD SOURCE             0: MIC 1: USB 2: REAR (RTTY/DATA Jack) 3: AUTO                                          1
                                    15   USB MOD GAIN           000 - 100                                                                               3
                                    16   REAR MOD GAIN          000 - 100                                                                               3
                                    17   RPTT SELECT            0: OFF 1: RTS 2: DTR 3: DAKY (RTTY/DATA Jack)                                           1
                                                                00: 50      01:100     02: 150   03: 200     04: 250   05: 300   06: 350  07: 400
                                    18   NAR WIDTH              08: 450     09: 500    10: 600   11: 800     12: 1200 13: 1400   14: 1700 15: 2000      2
                                                                16: 2400 17: 3000 18: 3200 19: 3500 20: 4000 (Hz)
                                    19   PSK TONE               0: 1000Hz 1: 1500Hz 2: 2000Hz                                                           1
                                    20   DATA SHIFT (SSB)       0 - 3000 Hz (P4 = 0000 - 3000, 10 Hz steps)                                             4
```

Table 2 (MENU Chart)

```text
        P1                P2        P3           Function                                                     P4                                         Digits
                                    01   AF TREBLE GAIN            -20 - -00 (or +00) - +10 (P4 = -20 - -00 or +00 - +10)                                  3
                                    02   AF MIDDLE TONE GAIN       -20 - -00 (or +00) - +10 (P4 = -20 - -00 or +00 - +10)                                  3
                                    03   AF BASS GAIN              -20 - -00 (or +00) - +10 (P4 = -20 - -00 or +00 - +10)                                  3
                                    04   AGC FAST DELAY            20 - 4000 msec (P4= 0020 - 4000, 20 msec/step)                                          4
                                    05   AGC MID DELAY             20 - 4000 msec (P4= 0020 - 4000, 20 msec/step)                                          4
                                    06   AGC SLOW DELAY            20 - 4000 msec (P4= 0020 - 4000, 20 msec/step)                                          4
                                    07   LCUT FREQ                 00: OFF 01: 100 Hz - 19: 1000 Hz (50 Hz steps)                                          2
                                    08   LCUT SLOPE                0: 6 dB/oct 1: 18 dB/oct                                                                1
                                    09   HCUT FREQ                 00: OFF 01: 700 Hz - 67: 4000 Hz (50 Hz steps)                                          2
         01               05
  (RADIO SETTING)     (MODE RTTY)   10   HCUT SLOPE                0: 6 dB/oct 1: 18 dB/oct                                                                1
                                    11   USB OUT LEVEL             000 - 100                                                                               3
                                    12   REAR OUT LEVEL            000 - 100                                                                               3
                                    13   RPTT SELECT               0: OFF 1: RTS 2: DTR 3: DAKY (RTTY/DATA Jack)                                           1
                                                                   00: 50      01:100     02: 150   03: 200     04: 250   05: 300 06: 350  07: 400
                                    14   NAR WIDTH                 08: 450     09: 500    10: 600   11: 800     12: 1200 13: 1400 14: 1700 15: 2000        2
                                                                   16: 2400 17: 3000 18: 3200 19: 3500 20: 4000 (Hz)
                                    15   MARK FREQUENCY            1: 1275 Hz 2: 2125 Hz                                                                   1
                                    16   SHIFT FREQUENCY           1: 170 Hz 1: 200 Hz 2: 425 Hz 3: 850 Hz                                                 1
                                    17   POLARITY-TX               0: NOR 1: REV                                                                           1
                                    01   AF TREBLE GAIN            -20 - -00 (or +00) - +10 (P4 = -20 - -00 or +00 - +10)                                  3
                                    02   AF MIDDLE TONE GAIN       -20 - -00 (or +00) - +10 (P4 = -20 - -00 or +00 - +10)                                  3
                                    03   AF BASS GAIN              -20 - -00 (or +00) - +10 (P4 = -20 - -00 or +00 - +10)                                  3
                                    04   AGC FAST DELAY            20 - 4000 msec (P4= 0020 - 4000, 20 msec/step)                                          4
                                    05   AGC MID DELAY             20 - 4000 msec (P4= 0020 - 4000, 20 msec/step)                                          4
                                    06   AGC SLOW DELAY            20 - 4000 msec (P4= 0020 - 4000, 20 msec/step)                                          4
                                    07   LCUT FREQ                 00: OFF 01: 100 Hz - 19: 1000 Hz (50 Hz steps)                                          2
                                    08   LCUT SLOPE                0: 6 dB/oct 1: 18 dB/oct                                                                1
                                    09   HCUT FREQ                 00: OFF 01: 700 Hz - 67: 4000 Hz (50 Hz steps)                                          2
                                    10   HCUT SLOPE                0: 6 dB/oct 1: 18 dB/oct                                                                1
                         01         11   USB OUT LEVEL             000 - 100                                                                               3
                      (MODE CW)     12   REAR OUT LEVEL            000 - 100                                                                               3
                                    13   RPTT SELECT               0: OFF 1: RTS 2: DTR 3: DAKY (RTTY/DATA Jack)                                           1
                                                                   00: 50      01:100     02: 150   03: 200     04: 250   05: 300 06: 350  07: 400
                                    14   NAR WIDTH                 08: 450     09: 500    10: 600   11: 800     12: 1200 13: 1400 14: 1700 15: 2000        2
                                                                   16: 2400 17: 3000 18: 3200 19: 3500 20: 4000 (Hz)
        02                          15   PC KEYING                 0: OFF 1: RTS 2: DTR 3: DAKY (RTTY/DATA Jack)                                           1
   (CW SETTING)
                                    16   CW BK-IN TYPE             0: SEMI 1: FULL                                                                         1
                                    17   CW WAVE SHAPE             0: 4 msec 1: 6 msec 2: 8 msec                                                           1
                                    18   CW FREQ DISPLAY           0: DIRECT FREQ 1: PITCH OFFSET                                                          1
                                    19   QSK DELAY TIME            0: 15 msec 1: 20 msec 2: 25 mesc 3: 30 msec                                             1
                                    20   CW INDICATOR              0: OFF 1: ON                                                                            1
                                    01   KEYER TYPE                0: OFF 1: BUG 2: ELEKEY-A 3: ELEKEY-B 4: ELEKEY-Y 5: ACS                                1
                                    02   KEYER DOT/DASH            0: NOR 1: REV                                                                           1
                                    03   CW WEIGHT                 2.5 - 4.5 (P4 = 25 - 45)                                                                2
                                    04   NUMBER STYLE              0: 1290 1: AUNO 2: AUNT 3: A2NO 4: A2NT 5: 12NO 6: 12NT                                 1
                                    05   CONTEST NUMBER            0001 - 9999                                                                             4
                                    06   CW MEMORY 1               0: TEXT 1: MESSAGE                                                                      1
                        (KEYER)
                                    07   CW MEMORY 2               0: TEXT 1: MESSAGE                                                                      1
                                    08   CW MEMORY 3               0: TEXT 1: MESSAGE                                                                      1
                                    09   CW MEMORY 4               0: TEXT 1: MESSAGE                                                                      1
                                    10   CW MEMORY 5               0: TEXT 1: MESSAGE                                                                      1
                                    11   REPEAT INTERVAL           1 - 60 sec (P4 = 01 - 60)                                                               2
                                    01   BEEP LEVEL                000 - 100                                                                               3
                                    02   RF/SQL VR                 0: RF 1: SQL 2:SQL (FM MODE only)                                                       1
                                    03   TUN/LIN PORT SELECT       0: EXT-TUNER 1: LINEAR 2: CAT-3 3: GPO                                                  1
                                    04   TUNER TYPE SELECT         0: INT 1: INT (FAST) 2: EXT 3: ATAS                                                     1
                                    05   CAT-1 RATE                0: 4800 bps 1: 9600 bps 2: 19200 bps 3: 38400 bps 4:115200 bps                          1
                                    06   CAT-1 TIME OUT TIMER      0: 10 msec 1: 100 msec 2: 1000 msec 3: 3000 msec                                        1
                                    07   CAT-1 CAT-3 STOP BIT      0: 1 bit 1: 2 bit                                                                       1
                                    08   CAT-2 RATE                0: 4800 bps 1: 9600 bps 2: 19200 bps 3: 38400 bps 4:115200 bps                          1
                                    09   CAT-2 TIME OUT TIMER      0: 10 msec 1: 100 msec 2: 1000 msec 3: 3000 msec                                        1
                                    10   CAT-3 RATE                0: 4800 bps 1: 9600 bps 2: 19200 bps 3: 38400 bps 4:115200 bps                          1
                                    11   CAT-3 TIME OUT TIMER      0: 10 msec 1: 100 msec 2: 1000 msec 3: 3000 msec                                        1
                                    12   QMB CH                    0: 5ch 1: 10ch                                                                          1
                                    13   BAND STACK                0: OFF 1: ON                                                                            1
        03                01        14   MEM GROUP                 0: OFF 1: ON                                                                            1
(OPERATION SETTING)   (GENERAL)     15   TX TIME OUT TIMER         00: OFF 01: 01 min - 30: 30 min (P4= 00 - 30)                                           2
                                    16   MIC SCAN                  0: OFF 1: ON                                                                            1
                                    17   MIC SCAN RESUME           0: PAUSE 1: TIME                                                                        1
                                    18   REF FREQ ADJ                -25 - +00 (or -00) - +25 (P4= -25 - +00 or -00 - +25)                                 3
                                                                     00: JAPANESE              01: ENGLISH(US)               02: ENGLISH(UK)
                                                                     03: FRENCH                04: FRENCH(CA)                05: GERMAN
                                    19   KEYBOARD LANGUAGE                                                                                                 2
                                                                     06: PORTUGUESE            07: PORTUGUESE(BR)            08: SPANISH
                                                                     09: SPANISH(LATAM)        10: ITALIAN
                                    20   MIC P1
                                    21   MIC P2                      00:LOCK           01:QMB             02:A/B             03:V/M       04:TUNER
                                    22   MIC P3                      05:VOX/MOX        06:MODE            07:ZIN_SPOT        08:SPLIT     09:FINE
                                                                     10:NAR            11:NB              12:DNR             13:FREQ UP   14:FREQ DOWN     2
                                    23   MIC P4                      15:BAND UP        16:BAND DOWN       17 ATT             18:IPO       19:DNF
                                    24   MIC UP                      20:AGC
                                    25   MIC DOWN
                                    26   SCU-LAN10                   0: OFF    1: ON                                                                       1
```

Table 2 (MENU Chart)

```text
        P1                  P2          P3           Function                                                     P4                             Digits
                                        01   IF NOTCH WIDTH            0: NARROW 1: WIDE                                                           1
                                        02   NB REJECTION              0: LOW 1: MID 2: HIGH                                                       1
                            02          03   NB WIDTH                  0: NARROW 1: MEDIUM 2: WIDE                                                 1
                         (RX-DSP)       04   APF WIDTH                 0: NARROW 1: MEDIUM 2: WIDE                                                 1
                                        05   CONTOUR LEVEL             -40 - -00 (or +00) - +20 (P4 = -40 - -00 or +00 - +20)                      3
                                        06   CONTOUR WIDTH             01 - 11                                                                     2
                                        01   AMC RELEASE TIME          0: FAST 1: MID 2: SLOW                                                      1
                                        02   PRMTRC EQ1 FREQ           00 : OFF 01: 100 Hz - 07: 700 Hz (100 Hz steps)                             2
                                        03   PRMTRC EQ1 LEVEL          -20 - -00 (or +00) - +10 (P4 = -20 - -00 or +00 - +10)                      3
                                        04   PRMTRC EQ1 BWTH           00 - 10                                                                     2
                                        05   PRMTRC EQ2 FREQ           00: OFF 01: 700 Hz - 09: 1500 Hz (100 Hz steps)                             2
                                        06   PRMTRC EQ2 LEVEL          -20 - -00 (or +00) - +10 (P4 = -20 - -00 or +00 - +10)                      3
                                        07   PRMTRC EQ2 BWTH           00 - 10                                                                     2
                                        08   PRMTRC EQ3 FREQ           00 : OFF 01: 1500 Hz - 18: 3200 Hz (100 Hz steps)                           2
                                        09   PRMTRC EQ3 LEVEL          -20 - -00 (or +00) - +10 (P4 = -20 - -00 or +00 - +10)                      3
                                        10   PRMTRC EQ3 BWTH           00 - 10                                                                     2
                        (TX AUDIO)
                                        11   P PRMTRC EQ1 FREQ         00 : OFF 01: 100 Hz - 07: 700 Hz (100 Hz steps)                             2
                                        12   P PRMTRC EQ1 LEVEL        -20 - -00 (or +00) - +10 (P4 = -20 - -00 or +00 - +10)                      3
                                        13   P PRMTRC EQ1 BWTH         00 - 10                                                                     2
                                        14   P PRMTRC EQ2 FREQ         00: OFF 01: 700 Hz - 09: 1500 Hz (100 Hz steps)                             2
```

(OPERATION SETTING)

```text
                                        15   P PRMTRC EQ2 LEVEL        -20 - -00 (or +00) - +10 (P4 = -20 - -00 or +00 - +10)                      3
                                        16   P PRMTRC EQ2 BWTH         00 - 10                                                                     2
                                        17   P PRMTRC EQ3 FREQ         00 : OFF 01: 1500 Hz - 18: 3200 Hz (100 Hz steps)                           2
                                        18   P PRMTRC EQ3 LEVEL        -20 - -00 (or +00) - +10 (P4 = -20 - -00 or +00 - +10)                      3
                                        19   P PRMTRC EQ3 BWTH         00 - 10                                                                     2
                                        01   HF MAX POWER              5 - 100 (P4 = 005 - 100)                                                    3
                                        02   50M MAX POWER             5 - 100 (P4 = 005 - 100)                                                    3
                                        03   70M MAX POWER             5 - 50 (P4 = 005 - 050)                                                     3
                            04          04   AM MAX POWER              5 - 25 (P4 = 005 - 025)                                                     3
                       (TX GENERAL)     05   VOX SELECT                0: MIC 1: USB 2: REAR (RTTY/DATA Jack)                                      1
                                        06   EMERGENCY FREQ TX         0: OFF 1: ON                                                                1
                                        07   TX INHIBIT                0: OFF 1: ON                                                                1
                                        08   METER DETECTOR            0: AVERAGE 1: PEAK                                                          1
                                        01   SSB/CW DIAL STEP          0: 5 1: 10 2: 20 (Hz)                                                       1
                                        02   RTTY/PSK DIAL STEP        0: 5 1: 10 2: 20 (Hz)                                                       1
                            05          03   CH STEP                   0: 1 1: 2.5 2: 5 3: 10 (kHz)                                                1
                         (TUNING)       04   AM CH STEP                0: 2.5 1: 5 2: 9 3: 10 4: 12.5 5: 25 (kHz)                                  1
                                        05   FM CH STEP                0: 5 1: 6.25 2: 10 3: 12.5 4: 20 5: 25 (kHz)                                1
                                        06   MAIN STEPS PER REV.       0: 50 1: 100 2: 200                                                         1
                                        01   MY CALL                   Up to 12 characters                                                        12
                                        02   MY CALL TIME              0: OFF 1: 1 2: 2 3: 3 4: 4 5: 5 (sec)                                       1
                             01         03   POP-UP TIME               0: FAST 1: MID 2: SLOW                                                      1
                         (DISPLAY)      04   SCREEN SAVER              0: OFF 1: 15 2: 30 3: 60 (min)                                              1
                                        05   DIMMER LED                00 - 20                                                                     2
                                        06   MOUSE POINTER SPEED 00 - 20                                                                           2
                                        01   RBW                       0: HIGH 1: MID 2: LOW                                                       1
        04                  02          02   SCOPE CTR                 0: FILTER 1: CARRIER POINT                                                  1
 (DISPLAY SETTING)       (SCOPE)        03   2D DISP SENSITIVITY       0: NORMAL 1: HI                                                             1
                                        04   3DSS DISP SENSITIVITY     0: NORMAL 1: HI                                                             1
                                        01   VMI COLOR VFO-A           0: BLUE 1: GREEN 2: WHITE 3: NONE                                           1
                             03         02   VMI COLOR VFO-B           0: BLUE 1: GREEN 2: WHITE 3: NONE                                           1
                      (VFO IND COLOR)   03   VMI COLOR MEMORY          0: BLUE 1: GREEN 2: WHITE 3: NONE                                           1
                                        04   VMI COLOR CLAR            0: RED 1: NONE                                                              1
                            04          01   EXT DISPLAY               0: OFF 1: ON                                                                1
                      (EXT-MONITOR)     02   PIXEL                     0: 800x480 1: 800x600                                                       1
                                        01   PRESET NAME               Up to 12 characters                                                        12
                                        02   CAT-1 RATE                0: 4800 bps 1: 9600 bps 2: 19200 bps 3: 38400 bps 4:115200 bps              1
                                        03   CAT-1 TIME OUT TIMER      0: 10 msec 1: 100 msec 2: 1000 msec 3: 3000 msec                            1
                           01           04   CAT-1 CAT-3 STOP BIT      0: 1 bit 1: 2 bit                                                           1
                        (PRESET1)       05   AGC FAST DELAY            20 - 4000 (P4 = 0020 - 4000, 20 msec steps)                                 4
                                        06   AGC MID DELAY             20 - 4000 (P4 = 0020 - 4000, 20 msec steps)                                 4
                        (PRESET2)       07   AGC SLOW DELAY            20 - 4000 (P4 = 0020 - 4000, 20 msec steps)                                 4
                                        08   LCUT FREQ                 00: OFF 01: 100 Hz - 19: 1000 Hz (50 Hz steps)                              2
        06                 03           09   LCUT SLOPE                0: 6dB/oct 1: 18dB/oct                                                      1
(EXTENSION SETTING)     (PRESET3)
                                        10   HCUT FREQ                 00: OFF 01:700Hz - 67:4000Hz (50 Hz steps)                                  2
                           04           11   HCUT SLOPE                0: 6dB/oct 1: 18dB/oct                                                      1
                        (PRESET4)       12   USB OUT LEVEL             000 - 100                                                                   3
                                        13   REAR OUT LEVEL            000 - 100                                                                   3
                        (PRESET5)       14   TX BPF SEL                0: 50 - 3050 1: 100 - 2900 2: 200 - 2800 3: 300 - 2700 4: 400 - 2600 Hz     1
                                        15   MOD SOURCE                0: MIC 1: USB 2: REAR (RTTY/DATA Jack) 3: AUTO                              1
                                        16   USB MOD GAIN              000 - 100                                                                   3
                                        17   REAR MOD GAIN             000 - 100                                                                   3
                                        18   RPTT SELECT               0: OFF 1: RTS 2:DTR 3:DAKY (RTTY/DATA Jack)                                 1




```

### FA — FREQUENCY VFO-A

```text
         1   2    3    4   5   6   7   8   9   10   11   12   P1 000030000 - 075000000 (Hz)
Set
         F   A    P1 P1 P1 P1 P1 P1 P1 P1 P1              ;
         1   2    3    4   5   6   7   8   9   10   11   12
Read
         F   A    ;
         1   2    3    4   5   6   7   8   9   10   11   12
Answer
         F   A    P1 P1 P1 P1 P1 P1 P1 P1 P1              ;


```

### FB — FREQUENCY VFO-B

```text
         1   2    3    4   5   6   7   8   9   10   11   12   P1 000030000 - 075000000 (Hz)
Set
         F   B    P1 P1 P1 P1 P1 P1 P1 P1 P1              ;
         1   2    3    4   5   6   7   8   9   10   11   12
Read
         F   B    ;
         1   2    3    4   5   6   7   8   9   10   11   12
Answer
         F   B    P1 P1 P1 P1 P1 P1 P1 P1 P1              ;


```

### FN — FINE TUNING

```text
         1   2    3    4   5   6   7   8   9   10   P1 0: “OFF”
Set
         F   N    P1   ;                               1: Fine Tuning “ON”
         1   2    3    4   5   6   7   8   9   10      2: Fast Tuning “ON”
Read
         F   N    ;
         1   2    3    4   5   6   7   8   9   10
Answer
         F   N    P1   ;


```

### FT — FUNCTION TX

```text
         1   2    3    4   5   6   7   8   9   10   P1 0: MAIN Band Transmitter: TX
Set
         F   T    P1   ;                               1: SUB Band Transmitter: TX
         1   2    3    4   5   6   7   8   9   10
Read
         F   T    ;
         1   2    3    4   5   6   7   8   9   10
Answer
         F   T    P1   ;


```

### GP — GP OUT

```text
         1   2    3    4   5   6   7   8   9   10   P1 0: GP OUT A “LOW”                            TUNER/LINEAR Jack
                                                         1: GP OUT A “HIGH”
Set                                                 P2 0: GP OUT B “LOW”
         G   P    P1 P2 P3 P4      ;                                                                          ⑦ GP OUT D
                                                         1: GP OUT B “HIGH”
                                                    P3 0: GP OUT C “LOW”                                ⑧         ⑥ GP OUT C
         1   2    3    4   5   6   7   8   9   10        1: GP OUT C “HIGH”
Read                                                P4 0: GP OUT D “LOW”                  ⑤ GP OUT B                  ③ GND
                                                         1: GP OUT D “HIGH”
         G   P    ;                                                                           ④ GP OUT A
                                                    *5V TTL Level, Max. 3 mA
                                                                                                        ②          ① +13V OUT
                                                    Set to “GP OUT” in the setting menu
         1   2    3    4   5   6   7   8   9   10
                                                    [OPERATION SETTING] → [GENERAL]
Answer                                              → [TUN/LIN PORT SELECT]. (Factory              (as viewed from rear panel)
         G   P    P1 P2 P3 P4      ;                setting: “EXT-TUNER”)



```

### GT — AGC FUNCTION

```text
         1   2    3    4   5   6   7   8   9   10   P1 0: (Fixed)     P3 0: AGC “OFF”
Set                                                 P2 0: AGC “OFF”		    1: AGC “FAST”
         G   T    P1 P2    ;
                                                       1: AGC “FAST”		   2: AGC “MID”
         1   2    3    4   5   6   7   8   9   10
Read                                                   2: AGC “MID”		    3: AGC “SLOW”
         G   T    P1   ;                               3: AGC “SLOW”		   4: AGC “AUTO - FAST”
         1   2    3    4   5   6   7   8   9   10      4: AGC “AUTO”		   5: AGC “AUTO - MID”
Answer                                                 		                6: AGC “AUTO - SLOW”
         G   T    P1 P3    ;


```

### ID — IDENTIFICATION

```text
         1   2    3    4   5   6   7   8   9   10   P1 0800 (Fixed)
Set
         1   2    3    4   5   6   7   8   9   10
Read
         I   D    ;
         1   2    3    4   5   6   7   8   9   10
Answer
         I   D    P1 P1 P1 P1      ;




```

### IF — INFORMATION VFO-A

```text
         1    2     3    4    5    6    7    8    9     10 P1 000: VFO or MT or QMB (3 Bytes)
Set                                                            001 - 099: (Memory Channel)
                                                               P1L - P9U: (PMS)
                                                               5xx: (5MHz BAND)
         1    2     3    4    5    6    7    8    9     10     EMG: (EMERGENCY CH)
Read                                                       P2 VFO-A Frequency (Hz) (9 Bytes)
         I    F     ;                                      P3 Clarifier Direction +: Plus Shift, -: Minus Shift (1 Bytes)
                                                               Clarifier Offset: 0000 - 9990 (Hz) (4 Bytes)
         1    2     3    4    5    6    7    8    9     10
                                                           P4 0: RX CLAR “OFF”          1: RX CLAR “ON”
                                                           P5 0: TX CLAR “OFF”          1: TX CLAR “ON”
         I    F    P1 P1 P1 P2 P2 P2 P2                 P2 P6 MODE 0:-               1: LSB          2: USB       3: CW-U 4: FM        5: AM
         11   12    13   14   15   16   17   18   19    20 		            6: RTTY-L 7: CW-L           8: DATA-L 9: RTTY-U A: DATA-FM
Answer                                                     		            B: FM-N     C: DATA-U D: AM-N            E: PSK  F: DATA-FM-N
         P2 P2 P2 P2 P3 P3 P3 P3 P3                     P4 P7 0: VFO 1: Memory Channel 2: Memory Tune 3: Quick Memory Bank (QMB)
                                                               4: -        5: PMS
         21   22    23   24   25   26   27   28   29    30 P8 0: OFF       1: CTCSS ENC/DEC 2: CTCSS ENC
                                                           P9 00: (Fixed)
         P5 P6 P7 P8 P9 P9 P10               ;             P10 0: Simplex 1: Plus Shift 2: Minus Shift



```

### IS — IF-SHIFT

```text
         1    2     3    4    5    6    7    8    9     10   P1   0: (Fixed)
Set
         I    S    P1 P2 P3 P4 P4 P4 P4                  ;   P2   0: (Fixed)
         1    2     3    4    5    6    7    8    9     10   P3   +/-
Read                                                         P4   0 - 1200 Hz (20 Hz steps)
         I    S    P1    ;
         1    2     3    4    5    6    7    8    9     10
Answer
         I    S    P1 P2 P3 P4 P4 P4 P4                  ;


```

### KM — KEYER MEMORY

```text
         1    2     3    4    5    6    7    ~    n-1   n    P1 1 - 5 : Keyer Memory Channel Number
Set
         K    M    P1 P2 P2 P2 P2            ~    P2     ;   P2 Message Characters (up to 50 characters)
         1    2     3    4    5    6    7    8    9     10
Read
         K    M    P1    ;
         1    2     3    4    5    6    7    ~    n-1   n
Answer
         K    M    P1 P2 P2 P2 P2            ~    P2     ;


```

### KP — KEY PITCH

```text
         1    2     3    4    5    6    7    8    9     10   P1 00: 300 Hz - 75: 1050 Hz (10Hz steps)
Set
         K    P    P1 P1      ;
         1    2     3    4    5    6    7    8    9     10
Read
         K    P     ;
         1    2     3    4    5    6    7    8    9     10
Answer
         K    P    P1 P1      ;


```

### KR — KEYER

```text
         1    2     3    4    5    6    7    8    9     10   P1 0: CW KEYER “OFF”
Set
         K    R    P1    ;                                      1: CW KEYER “ON”
         1    2     3    4    5    6    7    8    9     10
Read
         K    R     ;
         1    2     3    4    5    6    7    8    9     10
Answer
         K    R    P1    ;


```

### KS — KEY SPEED

```text
         1    2     3    4    5    6    7    8    9     10   P1 004 - 060 (WPM)
Set
         K    S    P1 P1 P1        ;
         1    2     3    4    5    6    7    8    9     10
Read
         K    S     ;
         1    2     3    4    5    6    7    8    9     10
Answer
         K    S    P1 P1 P1        ;


```

### KY — CW KEYING

```text
         1    2     3    4    5    6    7    8    9     10   P1 0: CW TEXT Memory 1: CW MESSAGE Memory
Set                                                          P2 0: STOP
         K    Y    P1 P2      ;
                                                                1: CW TEXT/MESSAGE Memory “1” Playback
         1    2     3    4    5    6    7    8    9     10
Read                                                            2: CW TEXT/MESSAGE Memory “2” Playback
                                                                3: CW TEXT/MESSAGE Memory “3” Playback
         1    2     3    4    5    6    7    8    9     10      4: CW TEXT/MESSAGE Memory “4” Playback
Answer                                                          5: CW TEXT/MESSAGE Memory “5” Playback




```

### LK — LOCK

```text
         1   2   3    4   5   6   7   8   9   10   P1 0: Lock “OFF”
Set
         L   K   P1   ;                               1: Lock “ON”
         1   2   3    4   5   6   7   8   9   10
Read
         L   K   ;
         1   2   3    4   5   6   7   8   9   10
Answer
         L   K   P1   ;


```

### LM — LOAD MESSAGE

```text
         1   2   3    4   5   6   7   8   9   10   P1 0: MESSAGE (DVS)     1: RECORD
Set                                                P2 P1=0 (MESSAGE)
         L   M   P1 P2    ;                        		 0: Play Stop/ Recording Stop
                                                   		 1: Select CH “1”
         1   2   3    4   5   6   7   8   9   10   		 2: Select CH “2”
Read                                               		 3: Select CH “3”
         L   M   P1   ;                            		 4: Select CH “4”
                                                   		 5: Select CH “5”
         1   2   3    4   5   6   7   8   9   10      P1=1 (RECORD)
Answer                                             		 0: Recording Stop
         L   M   P1 P2    ;                        		 1: Recording Start



```

### MA — MEMORY CHANNEL TO VFO-A

```text
         1   2   3    4   5   6   7   8   9   10
Set
         M   A   ;
         1   2   3    4   5   6   7   8   9   10
Read
         1   2   3    4   5   6   7   8   9   10
Answer


```

### MB — MEMORY CHANNEL TO VFO-B

```text
         1   2   3    4   5   6   7   8   9   10
Set
         M   B   ;
         1   2   3    4   5   6   7   8   9   10
Read
         1   2   3    4   5   6   7   8   9   10
Answer


```

### MC — MEMORY CHANNEL

```text
         1   2   3    4   5   6   7   8   9   10   P1 001-099: (Memory Channel)
Set
         M   C   P1 P1 P1     ;                       P1L -P9U: (PMS)
         1   2   3    4   5   6   7   8   9   10      5xx: (5MHz BAND)
Read                                                  EMG: (EMERGENCY CH)
         M   C   ;
         1   2   3    4   5   6   7   8   9   10
Answer
         M   C   P1 P1 P1     ;


```

### MD — OPERATING MODE

```text
         1   2   3    4   5   6   7   8   9   10   P1 0: MAIN Band
Set
         M   D   P1 P2    ;                           1: SUB Band
         1   2   3    4   5   6   7   8   9   10   P2 MODE 0:-         1: LSB      2: USB      3: CW-U     4: FM        5: AM
Read                                               		        6: RTTY-L 7: CW-L     8: DATA-L   9: RTTY-U   A: DATA-FM
         M   D   P1   ;                            		        B: FM-N   C: DATA-U   D: AM-N     E: PSK      F: DATA-FM-N
         1   2   3    4   5   6   7   8   9   10
Answer
         M   D   P1 P2    ;


```

### MG — MIC GAIN

```text
         1   2   3    4   5   6   7   8   9   10   P1 000 - 100
Set
         M   G   P1 P1 P1     ;
         1   2   3    4   5   6   7   8   9   10
Read
         M   G   ;
         1   2   3    4   5   6   7   8   9   10
Answer
         M   G   P1 P1 P1     ;




```

### ML — MONITOR LEVEL

```text
         1    2    3    4    5    6    7    8    9    10   P1 0: MONI “ON/OFF”
Set                                                           1: MONI Level
         M    L    P1 P2 P2 P2         ;
                                                           P2 P1=0
         1    2    3    4    5    6    7    8    9    10
Read                                                             000: MONI “OFF”
         M    L    P1   ;                                        001: MONI “ON”
         1    2    3    4    5    6    7    8    9    10      P1=1
Answer                                                           000 - 100
         M    L    P1 P2 P2 P2         ;


```

### MR — MEMORY CHANNEL READ

```text
         1    2    3    4    5    6    7    8    9    10 P0 001 - 099: (Memory Channel)
                                                             P1L - P9U: (PMS)
Set
                                                             5xx: (5MHz BAND)
                                                             EMG: (EMERGENCY CH)
                                                         P1 000: VFO or MT or QMB (3 Bytes)
         1    2    3    4    5    6    7    8    9    10     001 - 099: (Memory Channel)
Read                                                         P1L - P9U: (PMS)
         M    R    P0 P0 P0       ;                          5xx: (5MHz BAND)
                                                             EMG: (EMERGENCY CH)
         1    2    3    4    5    6    7    8    9    10 P2 Frequency (Hz) (9 Bytes)
                                                         P3 Clarifier Direction +: Plus Shift, -: Minus Shift,
                                                             Clarifier Offset: 0000 - 9990 (Hz) (5 Bytes)
         M    R    P1 P1 P1 P2 P2 P2 P2               P2 P4 0: RX CLAR “OFF”          1: RX CLAR “ON”
                                                         P5 0: TX CLAR “OFF”          1: TX CLAR “ON”
         11   12   13   14   15   16   17   18   19   20 P6 MODE 0:-               1: LSB          2: USB      3: CW-U 4: FM        5: AM
Answer                                                   		            6: RTTY-L 7: CW-L           8: DATA-L 9: RTTY-U A: DATA-FM
         P2 P2 P2 P2 P3 P3 P3 P3 P3                   P4 		            B: FM-N     C: DATA-U D: AM-N           E: PSK  F: DATA-FM-N
                                                         P7 0: VFO 1: Memory Channel 2: Memory Tune 3: Quick Memory Bank (QMB)
                                                             4: -        5: PMS
         21   22   23   24   25   26   27   28   29   30
                                                         P8 0: OFF 1: CTCSS ENC/DEC 2: CTCSS ENC
                                                         P9 00: (Fixed)
         P5 P6 P7 P8 P9 P9 P10              ;            P10 0: Simplex 1: Plus Shift 2: Minus Shift



```

### MS — METER SW

```text
         1    2    3    4    5    6    7    8    9    10   P1 0: PO
Set                                                            1: COMP
         M    S    P1 P2     ;
                                                               2: ALC
         1    2    3    4    5    6    7    8    9    10
Read                                                           3: VDD
         M    S    ;                                           4: ID
         1    2    3    4    5    6    7    8    9    10       5: SWR
Answer                                                     P2 0: (Fixed)
         M    S    P1 P2     ;


```

### MT — MEMORY CHANNEL TAG WRITE

```text
         1    2    3    4    5    6    7    8    9    10   P0 001 - 099: (Memory Channel)
         M    T    P0 P0 P0 P1 P2 P2 P2 P2                    P1L - P9U: (PMS)
Set                                                           5xx: (5MHz BAND)
         11   12   13   14   15   16   17   18   19
                                                              EMG: (EMERGENCY CH)
         P2 P2 P2 P2 P2 P2 P2 P2                 ;         P1 0: Memory Tag “OFF”
         1    2    3    4    5    6    7    8    9    10      1: Memory Tag “ON”
Read                                                       P2 TAG Characters (up to 12 characters) (ASCII code)
         M    T    P0 P0 P0       ;
         1    2    3    4    5    6    7    8    9    10
         M    T    P0 P0 P0 P1 P2 P2 P2 P2
Answer
         11   12   13   14   15   16   17   18   19
         P2 P2 P2 P2 P2 P2 P2 P2                 ;


```

### MW — MEMORY CHANNEL WRITE

```text
         1    2    3    4    5    6    7    8    9    10 P1 000: -
                                                             001 - 099: (Memory Channel)
         M    W    P1 P1 P1 P2 P2 P2 P2               P2     P1L - P9U: (PMS)
         11   12   13   14   15   16   17   18   19   20 P2 Frequency (Hz) (9 Bytes)
Set                                                      P3 Clarifier Direction +: Plus Shift, -: Minus Shift
         P2 P2 P2 P2 P3 P3 P3 P3 P3                   P4     Clarifier Offset: 0000 - 9990 (Hz) (5 Bytes)
                                                         P4 0: RX CLAR “OFF”          1: RX CLAR “ON”
         21   22   23   24   25   26   27   28   29   30 P5 0: TX CLAR “OFF”          1: TX CLAR “ON”
                                                         P6 MODE 0:-               1: LSB          2: USB     3: CW-U  4: FM        5: AM
         P5 P6 P7 P8 P9 P9 P10              ;
                                                         		            6: RTTY-L 7: CW-L           8: DATA-L 9: RTTY-U A: DATA-FM
         1    2    3    4    5    6    7    8    9    10 		            B: FM-N     C:  DATA-U      D: AM-N    E: PSK   F: DATA-FM-N
Read                                                     P7 0: VFO 1: Memory Channel 2: Memory Tune 3: Quick Memory Bank (QMB)
                                                             4: -        5: PMS
                                                         P8 0: OFF 1: CTCSS ENC/DEC 2: CTCSS ENC
         1    2    3    4    5    6    7    8    9    10
                                                         P9 00: (Fixed)
Answer                                                   P10 0: Simplex 1: Plus Shift 2: Minus Shift




```

### NA — NARROW

```text
         1    2    3    4    5    6    7    8    9    10   P1 0: (Fixed)
Set
         N    A    P1 P2     ;                             P2 0: OFF
         1    2    3    4    5    6    7    8    9    10      1: ON
Read
         N    A    P1   ;
         1    2    3    4    5    6    7    8    9    10
Answer
         N    A    P1 P2     ;


```

### NB — NOISE BLANKER STATUS

```text
         1    2    3    4    5    6    7    8    9    10   P1 0: (Fixed)
Set
         N    B    P1 P2     ;                             P2 0: Noise Blanker “OFF”
         1    2    3    4    5    6    7    8    9    10      1: Noise Blanker “ON”
Read
         N    B    P1   ;
         1    2    3    4    5    6    7    8    9    10
Answer
         N    B    P1 P2     ;


```

### NL — NOISE BLANKER LEVEL

```text
         1    2    3    4    5    6    7    8    9    10   P1 0: (Fixed)
Set
         N    L    P1 P2 P2 P2         ;                   P2 000 - 010
         1    2    3    4    5    6    7    8    9    10
Read
         N    L    P1   ;
         1    2    3    4    5    6    7    8    9    10
Answer
         N    L    P1 P2 P2 P2         ;


```

### NR — NOISE REDUCTION

```text
         1    2    3    4    5    6    7    8    9    10   P1 0: (Fixed)
Set
         N    R    P1 P2     ;                             P2 0: Noise Reduction “OFF”
         1    2    3    4    5    6    7    8    9    10      1: Noise Reduction “ON”
Read
         N    R    P1   ;
         1    2    3    4    5    6    7    8    9    10
Answer
         N    R    P1 P2     ;


```

### OI — OPPOSITE BAND INFORMATION (VFO-B)

```text
         1    2    3    4    5    6    7    8    9    10 P1 000: VFO or MT or QMB (3 Bytes)
Set                                                          001 - 099: (Memory Channel)
                                                             P1L - P9U: (PMS)
                                                             5xx: (5MHz BAND)
         1    2    3    4    5    6    7    8    9    10     EMG: (EMERGENCY CH)
Read                                                     P2 VFO-B Frequency (Hz) (9 Bytes)
         O    I    ;                                     P3 Clarifier Direction +: Plus Shift, -: Minus Shift
                                                             Clarifier Offset: 0000 - 9990 (Hz) (5 Bytes)
         1    2    3    4    5    6    7    8    9    10
                                                         P4 0: RX CLAR “OFF”          1: RX CLAR “ON”
                                                         P5 0: TX CLAR “OFF”          1: TX CLAR “ON”
         O    I    P1 P1 P1 P2 P2 P2 P2               P2 P6 MODE 0:-               1: LSB          2: USB     3: CW-U  4: FM        5: AM
         11   12   13   14   15   16   17   18   19   20 		            6: RTTY-L 7: CW-L           8: DATA-L 9: RTTY-U A: DATA-FM
Answer                                                   		            B: FM-N     C: DATA-U D: AM-N          E: PSK   F: DATA-FM-N
         P2 P2 P2 P2 P3 P3 P3 P3 P3                   P4 P7 0: VFO 1: Memory Channel 2: Memory Tune 3: Quick Memory Bank (QMB)
                                                             4: -        5: PMS
         21   22   23   24   25   26   27   28   29   30 P8 0: OFF       1: CTCSS ENC/DEC 2: CTCSS ENC
                                                         P9 00: (Fixed)
         P5 P6 P7 P8 P9 P9 P10              ;            P10 0: Simplex 1: Plus Shift 2: Minus Shift



```

### OS — OFFSET (REPEATER SHIFT)

```text
         1    2    3    4    5    6    7    8    9    10   P1 0: MAIN Band
Set
         O    S    P1 P2     ;                                  1: SUB Band
         1    2    3    4    5    6    7    8    9    10   P2 0: Simplex
Read                                                            1: Plus Shift (+ Offset)
         O    S    P1   ;
                                                                2: Minus Shift (- Offset)
         1    2    3    4    5    6    7    8    9    10
Answer                                                     *: This command can be activated only with an FM mode.
         O    S    P1 P2     ;


```

### PA — PRE-AMP (IPO)

```text
         1    2    3    4    5    6    7    8    9    10   P1 0: (Fixed)
Set
         P    A    P1 P2     ;                             P2 0: IPO
         1    2    3    4    5    6    7    8    9    10      1: AMP 1
Read                                                          2: AMP 2
         P    A    P1   ;
         1    2    3    4    5    6    7    8    9    10
Answer
         P    A    P1 P2     ;




```

### PB — PLAY BACK

```text
         1   2   3    4   5   6   7   8   9   10   P1 0: (Fixed)
Set                                                P2 0: MESSAGE Playback / Recording Stop
         P   B   P1 P2    ;
                                                      1: MESSAGE CH “1” Playback Start
         1   2   3    4   5   6   7   8   9   10
Read                                                  2: MESSAGE CH “2” Playback Start
         P   B   P1   ;                               3: MESSAGE CH “3” Playback Start
         1   2   3    4   5   6   7   8   9   10      4: MESSAGE CH “4” Playback Start
Answer                                                5: MESSAGE CH “5” Playback Start
         P   B   P1 P2    ;


```

### PC — POWER CONTROL

```text
         1   2   3    4   5   6   7   8   9   10   P1 005 - 100
Set
         P   C   P1 P1 P1     ;
         1   2   3    4   5   6   7   8   9   10
Read
         P   C   ;
         1   2   3    4   5   6   7   8   9   10
Answer
         P   C   P1 P1 P1     ;


```

### PL — SPEECH PROCESSOR LEVEL

```text
         1   2   3    4   5   6   7   8   9   10   P1 001 -100
Set
         P   L   P1 P1 P1     ;                    P2 000: “OFF”, 001 -100
         1   2   3    4   5   6   7   8   9   10
Read
         P   L   ;
         1   2   3    4   5   6   7   8   9   10
Answer
         P   L   P2 P2 P2     ;


```

### PR — SPEECH PROCESSOR

```text
         1   2   3    4   5   6   7   8   9   10   P1 0: Speech Processor
Set
         P   R   P1 P2    ;                           1: Parametric Microphone Equalizer
         1   2   3    4   5   6   7   8   9   10   P2 1: “OFF”
Read                                                  2: “ON”
         P   R   P1   ;
         1   2   3    4   5   6   7   8   9   10
Answer
         P   R   P1 P2    ;


```

### PS — POWER SWITCH

```text
         1   2   3    4   5   6   7   8   9   10   P1 0: POWER “OFF”
Set
         P   S   P1   ;                               1: POWER “ON”
         1   2   3    4   5   6   7   8   9   10
Read
         P   S   ;
         1   2   3    4   5   6   7   8   9   10
Answer
         P   S   P1   ;


```

### QI — QMB STORE

```text
         1   2   3    4   5   6   7   8   9   10
Set
         Q   I   ;
         1   2   3    4   5   6   7   8   9   10
Read
         1   2   3    4   5   6   7   8   9   10
Answer


```

### QR — QMB RECALL

```text
         1   2   3    4   5   6   7   8   9   10
Set
         Q   R   ;
         1   2   3    4   5   6   7   8   9   10
Read
         1   2   3    4   5   6   7   8   9   10
Answer


```

### RA — RF ATTENUATOR

```text
         1   2   3    4   5   6   7   8   9   10   P1 0: (Fixed)
Set
         R   A   P1 P2    ;                        P2 0: OFF
         1   2   3    4   5   6   7   8   9   10      1: 6dB
Read                                                  2: 12dB
         R   A   P1   ;
                                                      3: 18dB
         1   2   3    4   5   6   7   8   9   10
Answer
         R   A   P1 P2    ;




```

### RG — RF GAIN

```text
         1   2     3   4   5   6   7   8   9   10   P1 0: (Fixed)
Set
         R   G   P1 P2 P2 P2       ;                P2 000 - 255
         1   2     3   4   5   6   7   8   9   10
Read
         R   G   P1    ;
         1   2     3   4   5   6   7   8   9   10
Answer
         R   G   P1 P2 P2 P2       ;


```

### RI — RADIO INFORMATION

```text
         1   2     3   4   5   6   7   8   9   10   11   P1 0: (Fixed)
Set                                                      P2 0: Normal 1: Hi-SWR
                                                         P3 0: Stop 1: Recording 2: Playing
         1   2     3   4   5   6   7   8   9   10   11   P4 0: RX 1: TX 2: TX INHIBIT
Read                                                     P5 0: (Fixed)
         R   I   P1    ;
                                                         P6: 0: Antenna tuner: Tuning stopped 1:Antenna tuner: Tuning
         1   2     3   4   5   6   7   8   9   10   11   P7: 0: Scan Stop 1:Scanning 2:Scan Pause
Answer
         R   I   P1 P2 P3 P4 P5 P6 P7 P8             ;   P8: 0: SQL Closed 1: SQL Open (BUSY)



```

### RL — NOISE REDUCTION LEVEL (DNR)

```text
         1   2     3   4   5   6   7   8   9   10   P1 0: (Fixed)
Set
         R   L   P1 P2 P2      ;                    P2 01 - 15
         1   2     3   4   5   6   7   8   9   10
Read
         R   L   P1    ;
         1   2     3   4   5   6   7   8   9   10
Answer
         R   L   P1 P2 P2      ;


```

### RM — READ METER

```text
         1   2     3   4   5   6   7   8   9   10   P1=0
Set
                                                        P2: Meter 000 - 255
         1   2     3   4   5   6   7   8   9   10
                                                        P3: 000 (Fixed)
Read                                                P1= 1: S (Main Band) 2: -          3: COMP        4: ALC        5: PO
         R   M   P1    ;                                6: SWR           7: IDD        8: VDD
         1   2     3   4   5   6   7   8   9   10       P2: 000 - 255
Answer                                                  P3: 000 (Fixed)
         R   M   P1 P2 P2 P2 P3 P3 P3          ;


```

### SC — SCAN

```text
         1   2     3   4   5   6   7   8   9   10   P1 0: Scan “OFF”
Set
         S   C   P1    ;                               1: Scan “ON” (UP ward)
         1   2     3   4   5   6   7   8   9   10      2: Scan “ON” (DOWN ward)
Read
         S   C     ;
         1   2     3   4   5   6   7   8   9   10
Answer
         S   C   P1    ;


```

### SD — CW BREAK-IN DELAY TIME

```text
         1   2     3   4   5   6   7   8   9   10   00: 30       01: 50      02: 100    03: 150      04: 200      05: 250
Set                                                 06: 300 - 33: 3000 (msec)
         S   D   P1 P1     ;
         1   2     3   4   5   6   7   8   9   10
Read                                                NOTE: 06 to 33: 100 msec steps
         S   D     ;
         1   2     3   4   5   6   7   8   9   10
Answer
         S   D   P1 P1     ;


```

### SF — SUB DIAL FUNCTION

```text
         1   2     3   4   5   6   7   8   9   10   P1 0: FUNC knob
Set                                                    1: DSP knob
         S   F   P1 P2     ;                        P2 P1=0
                                                       0: -                1: SCOPE LEVEL         2: PEAK           3: COLOR
         1   2     3   4   5   6   7   8   9   10      4: CONTRAST         5: DIMMER              6: M-GROUP        7: MIC GAIN
Read                                                   8: PROC LEVEL       9: AMC LEVEL           A: VOX GAIN       B: VOX DELAY
         S   F   P1    ;                               C: ANTI VOX         D: RF POWER            E: MONI LEVEL     F: CW SPEED
                                                       G: CW PITCH         H: BK-DELAY
         1   2     3   4   5   6   7   8   9   10      P1=1
Answer                                                 0: -                1: SHIFT               2: WIDTH          3: NOTCH
         S   F   P1 P2     ;                           4: CONTOUR          5: APF




```

### SH — WIDTH

```text
         1   2   3    4     5        6     7       8        9   10    P1 0: (Fixed)
Set
         S   H   P1 P2 P3 P3               ;                          P2 0: (Fixed)
         1   2   3    4     5        6     7       8        9   10    P3 00 - 23 (See Table 3)
Read
         S   H   P1   ;
         1   2   3    4     5        6     7       8        9   10
Answer
         S   H   P1 P2 P3 P3               ;
```

Table 3 (Bandwidth Chart)

```text
                      Command                                                         Bandwidth
                                                                 CW / DATA-L /                            AM / FM-N /
                          P3                   LSB / USB                                   AM-N                             FM / DATA-FM
                                                                 DATA-U / PSK                              D-FM-N
                      00 (Default)             (Default)*            (Default)*              -                 -                  -
                          01                     300 Hz                 50 Hz          6000 Hz (Fixed)         -                  -
                          02                     400 Hz                100 Hz                -           9000 Hz (Fixed)          -
                          03                     600 Hz                150 Hz                -                 -           16000 Hz (Fixed)
                          04                     850 Hz                200 Hz                -                 -                  -
                          05                    1100 Hz                250 Hz                -                 -                  -
                          06                    1200 Hz                300 Hz                -                 -                  -
                          07                    1500 Hz                350 Hz                -                 -                  -
                          08                    1650 Hz                400 Hz                -                 -                  -
                          09                    1800 Hz                450 Hz                -                 -                  -
                          10                    1950 Hz                500 Hz                -                 -                  -
                           11                   2100 Hz                600 Hz                -                 -                  -
                          12                    2250 Hz                800 Hz                -                 -                  -
                          13                    2400 Hz               1200 Hz                -                 -                  -
                          14                    2450 Hz               1400 Hz                -                 -                  -
                          15                    2500 Hz               1700 Hz                -                 -                  -
                          16                    2600 Hz               2000 Hz                -                 -                  -
                          17                    2700 Hz               2400 Hz                -                 -                  -
                          18                    2800 Hz               3000 Hz                -                 -                  -
                          19                    2900 Hz               3200 Hz                -                 -                  -
                          20                    3000 Hz               3500 Hz                -                 -                  -
                          21                    3200 Hz               4000 Hz                -                 -                  -
                          22                    3500 Hz                  -                   -                 -                  -
                          23                    4000 Hz                  -                   -                 -                  -

                                         *(The default bandwidth varies depending on the selected mode.)

```

### SM — S-METER READING

```text
         1   2   3    4     5        6     7       8        9   10    P1 0: (Fixed)
Set
                                                                      P2 000 - 255
         1   2   3    4     5        6     7       8        9   10
Read
         S   M   P1   ;
         1   2   3    4     5        6     7       8        9   10
Answer
         S   M   P1 P2 P2 P2               ;


```

### SQ — SQUELCH LEVEL

```text
         1   2   3    4     5        6     7       8        9   10    P1 0: (Fixed)
Set
         S   Q   P1 P2 P2 P2               ;                          P2 000 - 100
         1   2   3    4     5        6     7       8        9   10
Read
         S   Q   P1   ;
         1   2   3    4     5        6     7       8        9   10
Answer
         S   Q   P1 P2 P2 P2               ;




```

### SS — SPECTRUM SCOPE

```text
         1     2   3    4   5   6   7   8   9   10   P1 0: (Fixed)
Set
         S   S     P1 P2 P3 P4 P5 P6 P7         ;    P2 0: SPEED      1: PEAK 2: MARKER 3: COLOR             4: LEVEL     5: SPAN
         1     2   3    4   5   6   7   8   9   10      6: MODE      7: AF-FFT/OSCILLOSCOPE
Read                                                   P2=0 (SPEED):
         S   S     P1 P2    ;
                                                     		 P3 0: SLOW1 1: SLOW2 2: FAST1 3: FAST2 4: FAST3 5: STOP
         1     2   3    4   5   6   7   8   9   10
Answer                                               		 P4 - P7: 0: (Fixed)
         S   S     P1 P2 P3 P4 P5 P6 P7         ;      P2=1 (PEAK):
                                                     		 P3 0: LV1 1: LV2 2: LV3 3: LV4 4: LV5
                                                     		 P4 - P7: 0: (Fixed)
                                                       P2=2 (MARKER):
                                                     		 P3 0: MARKER “OFF” 1: MARKER “ON”
                                                     		 P4 - P7: 0: (Fixed)
                                                       P2=3 (COLOR):
                                                     		 P3 0: COLOR-1 - A: COLOR-11
                                                     		 P4 - P7: 0: (Fixed)
                                                       P2=4 (LEVEL):
                                                     		 P3 - P7: -30.0 - -00.0 or +00.0 - +30.0 (0.5 dB steps, 5 bytes)
                                                       P2=5 (SPAN):
                                                     		 P3 0: 1 kHz        1: 2 kHz       2: 5 kHz     3: 10 kHz     4: 20 kHz      5: 50 kHz
                                                     			      6: 100 kHz 7: 200 kHz 8: 500 kHz 9: 1 MHz
                                                     		 P4 - P7: 0: (Fixed)
                                                       P2=6 (MODE):
                                                     		 P3 0: 3DSS CENTER                      1: 3DSS CURSOR                  2: 3DSS FIX
                                                     			      3: W/F CENTER (EXPAND)           4: W/F CENTER (NORMAL)          5: -
                                                     			      6: W/F CURSOR (EXPAND) 7: W/F CURSOR (NORMAL)                    8: -
                                                     			      9: W/F FIX (EXPAND)              A: W/F FIX (NORMAL)
                                                     		 P4 - P7: 0: (Fixed)
                                                       P2=7 (AF-FFT/OSCILLOSCOPE):
                                                     		 P3 0: AF-FFT (ATT=0dB)          1: AF-FFT (ATT=10dB)        2: AF-FFT (ATT=20dB)
                                                     		 P4 0: OSC Level (ATT=0dB) 1: OSC Level (ATT=10dB) 2: OSC Level (ATT=20dB)
                                                     		 P5 0: OSC Time (1 msec)         1: OSC Time (3 msec)        2: OSC Time (10 msec)
                                                     			      3: OSC Time (30 msec) 4: OSC Time (100 msec)          5: OSC Time (300 msec)
                                                     		 P6 - P7: 0: (Fixed)


```

### ST — SPLIT

```text
         1     2   3    4   5   6   7   8   9   10   P1 0: SPLIT “OFF”
Set
         S   T     P1   ;                               1: SPLIT “ON”
         1     2   3    4   5   6   7   8   9   10
Read
         S   T     ;
         1     2   3    4   5   6   7   8   9   10
Answer
         S   T     P1   ;


```

### SV — SWAP VFO

```text
         1     2   3    4   5   6   7   8   9   10   Changes the VFO-A and VFO-B
Set
         S   V     ;
         1     2   3    4   5   6   7   8   9   10
Read
         1     2   3    4   5   6   7   8   9   10
Answer


```

### TS — TXW

```text
         1     2   3    4   5   6   7   8   9   10   P1 0: TXW “OFF”
Set
         T   S     P1   ;                               1: TXW “ON”
         1     2   3    4   5   6   7   8   9   10
Read
         T   S     ;
         1     2   3    4   5   6   7   8   9   10
Answer
         T   S     P1   ;


```

### TX — TX SET

```text
         1     2   3    4   5   6   7   8   9   10   P1 0: RADIO TX “OFF”, CAT TX “OFF”
Set
         T   X     P1   ;                               1: RADIO TX “OFF”, CAT TX “ON”
         1     2   3    4   5   6   7   8   9   10      2: RADIO TX “ON”, CAT TX “OFF” (Answer)
Read
         T   X     ;
         1     2   3    4   5   6   7   8   9   10
Answer
         T   X     P1   ;




```

### UP — MIC UP

```text
         1   2     3   4   5   6   7   8   9   10
Set
         U   P     ;
         1   2     3   4   5   6   7   8   9   10
Read
         1   2     3   4   5   6   7   8   9   10
Answer


```

### VD — VOX DELAY TIME / DATA VOX DELAY TIME

```text
         1   2     3   4   5   6   7   8   9   10   P1 00: 30 msec     01: 50 msec 02: 100 msec       03: 150 msec     04: 200 msec
Set
         V   D    P1 P1 P1 P1      ;                   05: 250 msec    06: 300 msec - 33: 3000 msec (06 - 33: 10 msec multiples)
         1   2     3   4   5   6   7   8   9   10   NOTE: VD command sets individual parameter values with the setting values “MIC” and
Read
         V   D     ;                                “USB or REAR” in the menu items [OPERATION SETTING] → [TX GENERAL] → [VOX
         1   2     3   4   5   6   7   8   9   10   SELECT].
Answer
         V   D    P1 P1 P1 P1      ;


```

### VE — FIRMWARE VERSION

```text
         1   2     3   4   5   6   7   8   9   10   P1 0: MAIN CPU 1: DISPLAY CPU          2: SDR    3: DSP
Set                                                 P2 XX-XX (Binary Coded Decimal)
         1   2     3   4   5   6   7   8   9   10
Read
         V   E    P1   ;
         1   2     3   4   5   6   7   8   9   10
Answer
         V   E    P1 P2 P2 P2 P2       ;


```

### VG — VOX GAIN

```text
         1   2     3   4   5   6   7   8   9   10   P1 000 - 100
Set
         V   G    P1 P1 P1     ;
         1   2     3   4   5   6   7   8   9   10
Read
         V   G     ;
         1   2     3   4   5   6   7   8   9   10
Answer
         V   G    P1 P1 P1     ;


```

### VM — VFO / MEMORY CHANNEL

```text
         1   2     3   4   5   6   7   8   9   10
Set
         V   M     ;           ;
         1   2     3   4   5   6   7   8   9   10
Read
         1   2     3   4   5   6   7   8   9   10
Answer


```

### VS — VFO SELECT

```text
         1   2     3   4   5   6   7   8   9   10   P1 0: MAIN Band: VFO-A / SUB Band: VFO-B
Set
         V   S    P1   ;                               1: MAIN Band: VFO-B / SUB Band: VFO-A
         1   2     3   4   5   6   7   8   9   10
Read
         V   S     ;
         1   2     3   4   5   6   7   8   9   10
Answer
         V   S    P1   ;


```

### VX — VOX STATUS

```text
         1   2     3   4   5   6   7   8   9   10   P1 0: VOX “OFF”
Set
         V   X    P1   ;       ;                       1: VOX “ON”
         1   2     3   4   5   6   7   8   9   10
Read
         V   X     ;
         1   2     3   4   5   6   7   8   9   10
Answer
         V   X    P1   ;


```

### XT — TX CLAR

```text
         1   2     3   4   5   6   7   8   9   10   P1 0: TX CLAR “OFF”
Set
         X   T    P1   ;                               1: TX CLAR “ON”
         1   2     3   4   5   6   7   8   9   10
Read
         X   T     ;
         1   2     3   4   5   6   7   8   9   10
Answer
         X   T    P1   ;




```

### ZI — ZERO IN

```text
         1   2     3   4   5   6   7   8   9   10   (CW AUTO ZERO IN Function)
Set
         Z   I   P1    ;                            P1 0: Fixed
         1   2     3   4   5   6   7   8   9   10
Read
         1   2     3   4   5   6   7   8   9   10
Answer
```

## Copyright 2023

YAESU MUSEN CO., LTD. All rights reserved. No portion of this manual may be reproduced without the permission of YAESU MUSEN CO., LTD.

YAESU MUSEN CO., LTD. Omori Bellport Building D-3F 6-26-3 Minami-Oi, Shinagawa-ku, Tokyo, 140-0013, Japan YAESU USA 6125 Phyllis Drive, Cypress, CA 90630, U.S.A. YAESU UK Unit 12, Sun Valley Business Park, Winnall Close

```text
Winchester, Hampshire, SO23 0LB, U.K.                    2306-C
```
