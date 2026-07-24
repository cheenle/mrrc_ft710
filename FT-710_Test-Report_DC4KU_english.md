# Yaesu FT-710 Test Report

Werner Schnorrenberg, DC4KU — https://dc4ku.darc.de — 30.10.2022

The FT-710 is a modern, direct sampling HF/50/70MHz transceiver and is characterized by the following features: HF direct sampling with dual-channel ADC (14-bit), 3DSS real-time spectrum scope, RMDR 113dB in 2 kHz distance, dithering signal, 4.3 inch touch screen color display, AESS (Acustic Enhanced Speaker System), connection for external DVI-D monitor, antenna tuner and 100 Watt transmission power. FT-710 and FT-DX1/101 are constructed differently (Figure 1, 2). The FT-DX10 is a hybrid SDR with analog mixer, LO, roofing filter and A/D conversion of the IF. The FT-710 is a direct-sampling SDR, which digitizes the RF signals directly. For this he uses the same twin ADC as in the FT-DX10 and the subsequent FPGA combines their digital signals in such a way that an overload occurs late. In addition, a dithering signal (noise) fed into the inputs of the ADCs generates a reduction in IMD3 interference (1).

**Figure 3 shows the Yaesu specifications of the FT-710, such as RMDR, BDR, IMD3 and TX-Phase Noise.**

The most important RF data of the receiver and transmitter are tested below. A detailed report on the function and handling of the FT-710 will be published in FUNKAMATEUR magazine 01/2023.

**Figure 1: Yaesu block diagram of the FT-710, direct-sampling SDR**

**Figure 2: Yaesu block diagram of the FT-DX10, Hybrid SDR**

**Figure 3: Yaesu specifications of the FT-710**

## Receiver

### Sensitivity (Minimum Discernible Signal, MDS)

The sensitivity is defined as the size of the receiver noise floor (MDS, Minimum Discernible Signal). If a CW signal is applied to the input of the receiver whose level (Pi) raises the noise floor of the receiver by 3dB (voltage increase at the RMS voltmeter by a factor of 1.414), then the power of the signal according to (S+N)/N = 2 corresponds to the noise floor of the receiver. Set the overlay tone (LF) at the loudspeaker to approx. 700Hz. For this measurement, a calibrated RF generator, a switchable attenuator and a RMS-voltmeter are required (Fig. 4).

```text
   RF-Signal-                                            RMS
   Generator                                           Voltmeter

                          Pi     FT-710      Audio
                                Receiver
                                                  LF

                                                           +3dB
```

**Figure 4: Measurement setup to determine the sensitivity**

The following sensitivities (MDS) were measured in the frequency bands:

Settings: BW=500Hz (CW)

```text
                    1.9MHz        3.7MHz          7.1MHz           14.2MHz   21.2MHz    28.2MHz      50.1MHz
      IPO          -123dBm       -125dBm          -126dBm          -126dBm   -127dBm    -127dBm      -128dBm
  AMP1 (+10dB)     -132dBm       -135dBm          -136dBm          -136dBm   -136dBm    -136dBm      -138dBm
  AMP2 (+20dB)     -141dBm       -142 dBm       - 142 dBm          -142dBm   -142 dBm   -143 dBm     -141dBm
```

**Table 1: Sensitivity (MDS) for CW, BW = 500Hz**

Settings: BW=2.4kHz (SSB)

```text
                    1,9MHz        3,7MHz          7,1MHz           14,2MHz   21,2MHz    28,2MHz      50,1MHz
      IPO          -117dBm       -119 dBm         -120 dBm         -120dBm   -121 dBm   -121 dBm     -122 dBm
  AMP1 (+10dB)     -126dBm       -129dBm          -130dBm          -130dBm   -130dBm    -130dBm      -132dBm
 AMP2 ( +20dB)     -134dBm       -136dBm          -136dBm          -136dBm   -136dBm    -137dBm      -135dBm
```

**Table 2: Sensitivity (MDS) for SSB, BW = 2.4kHz**

### Noise Figure (NF)

With a noise limit value of -174dBm/Hz, the noise figure is calculated as follows: Noise Figure = MDS - 10logBW - (-174dBm/Hz). At BW=2.4 kHz, the following applies: Noise Figure = MDS + 140dB

```text
    Frequenz        1,9MHz        3,7MHz          7,1MHz           14,2MHz   21,2MHz    28,2MHz      50,1MHz
      IPO               23 dB      21 dB           20 dB            20 dB     19 dB      19 dB        18 dB
  AMP1 (+10dB)          14 dB      11 dB           10 dB            10 dB     10 dB      10 dB         8 dB
  AMP1 (+20dB)          6 dB       4 dB             4 dB            4 dB       4dB        3dB          5dB
```

**Table 3: Noise Figure**

Result: The sensitivity is sufficiently good on all bands. In the higher bands, the preamplifier AMP1 can be switched on if required, whereby the distortion-free dynamics are not affected, as will be shown later.

The term "IPO" stands for "Intercept Point Optimization". This means the optimization of the 3rd order intercept point. However, an IP3 does not exist for direct scanning SDRs. Presumably Yaesu accidentally adopted this designation from an analogue, superheterodyne receiver.

### RMDR and SBN

Reciprocal Mixing Dynamic Range (RMDR) and Sideband Noise (SBN) are among the most important criteria of a receiver. Excessive sideband noise can mask a small signal next to a large signal and "deaf" a receiver. Greater sensitivity or better selection does no longer help here. During the sampling process, the SBN of the clock generator mixes with the received signal, so that the signal can be covered by the noise under certain circumstances. The phase noise of the clock generator should therefore be as small as possible (<-140dBc/Hz) and the resulting RMDR as large as possible (>110 dB). To determine the RMDR, a quasi noise-free carrier signal (10MHz OCXO from KVG) is fed into the receiver and its level (Pi) is increased until a signal-to-noise ratio (S+N)/N of +3dB above the background noise (MDS) is obtained at a distance of 2 kHz (2).

From this the RMDR is calculated to RMDR = Pi - MDS and the SBN to SBN = -(RMDR + 10logB).

Reciprocal Mixing Dynamic Range (RMDR) -20dBm

```text
                 Testsignal                 RMDR = Pi - MDS

                                            110dB

                          SBN

      3dB above noise                                        MDS
                             2 kHz                                 DC4KU
```

**Figure 5: Determination of SBN and RMDR with a low-noise test signal**

With an MDS of -136dBm at BW = 500Hz and an offset of 2kHz, the FT-710 has an RMDR and SBN of

RMDR = Pi - MDS = -20dBm - (-136dBm) = 116dB

SBN = -(RMDR + 10logB) = -(116dB + 10log500Hz) = -(116 + 27)dBc/Hz = 143dBc/Hz

In the same way, the measurement is carried out at intervals of up to 100 kHz (Table 4), resulting in the measurement curves in Fig. 6.

```text
  Offset (kHz)    Pi (dBm)      SBN (dBc/Hz)        RMDR (dB)
       2             -20            -143              116
       5            -18              -145              118
      10            -17              -146              119
      20            -16              -147              120
      50            -15              -148              121
      100           -14              -149              122
```

**Table 4: RMDR and SBN in carrier spacing from 2 to 100 kHz**

```text
             130                                                                                         -120

                       RMDR                                                                                         SBN, Sideband Noise




                                                                               Phasenrauschen (dBc/Hz)
             120                                                                                         -130
 RMDR (dB)




             110                                                                                         -140



             100                                                                                         -150



             90                                                                                          -160
                   1                        10                       100                                        1                         10              100
                                  Frequenzabstand (kHz)                                                                     Frequenzabstand (kHz)
```

**Figure 6: RMDR (left) and phase noise (right) at a distance of 2kHz to 100kHz from the carrier**

Result: The RMDR and SBN of the FT-710 are very good. Small signals close to large signals are unaffected by the receiver's sideband (phase) noise.

### 3rd Order Intermodulation (IMD3, DR3)

To test the 3rd order intermodulation, the receiver is controlled with two equally large RF signals (f1 = 14.200 MHz, f2 = 14.202 MHz, delta f = 2kHz) and the intermodulation is measured at 2 x f1-f2 and 2 x f2-f1 (Figure 7). The level of the 2-tone signal is gradually increased in 1 dB steps up to the limit of the receiver and the resulting 3rd order intermodulation level is noted.

DR3 = Pi - MDS

f1

RMS Voltmeter Audio

```text
                                             f1+f2        FT-710      2f1-f2
              f2              +
                                                 Pi      Receiver
                                                                      2f2-f1

                                                                                                         +3dB

                                                                                                          DC4KU
```

**Figure 7: Measurement setup for IMD3 measurement**

**Table 5 shows the maximum achievable dynamic range (DR3), with and without a preamplifier.**

Settings: BW 500Hz; IPO, AMP1, AMP2: on/off

```text
 Amplifiers                        MDS                  Pi           DR3
 IPO                              -126dBm             -19dBm        107dB
 AMP1 (+10dB)                     -136dBm             -29dBm        107dB
 AMP2 (+20dB)                     -142dBm             -39dBm        103dB
```

**Table 5: DR3 of the FT-710 in the 20m band, with and without preamp, BW=500Hz**

The course of the resulting intermodulation is shown in Fig. 8. Without pre-amplification, the FT-710 achieves a maximum, distortion-free dynamic range of 107dB (green curve). The dynamic is calculated as

Pi - MDS = -19dBm - (-126dBm) = 107dB.

This is excellent value. With AMP1 (+10dB) the receiver achieves the same dynamic range of 107dB, which proves the large-signal immunity of the amplifier and the bandpass filter. Only when both preamplifiers (AMP2, +20dB) are switched on does the dynamics drop by 4dB . Below the maximum IM-free level (sweet spot) there are no IM products above the receiver background noise, which is unusual because most SDRs already produce IM here. Dithering obviously shows its positive effect here. There is no OVF (overflow) display on the FT-710. The receiver also does not clip, but always remains below its limit of 0dBFS (full scale) thanks to a separate AGC. Blocking does not appear until Pi = +2dBm (1.6mW).

-100

```text
                             f1 = 14,200 MHz                             FT-710
                    -105
                             f2 = 14,202 MHz
                             BW = 500Hz
                    -110

                             Urban Noise
                    -115

                             Rural Noise

                    -120     Quiet Noise
 IMD3, IFSS (dBm)




                    -125                             IPO (Preamp off)

                                                   MDS = -126dBm/500Hz
                                                                                                                      Sweet Spot
                    -130



                    -135                           AMP1 (+10dB)
                                                MDS = -136dBm/500Hz
                    -140                  AMP2 (+20dB)

                                    MDS = -142dBm/500Hz
                    -145
                                                                                    -39               -29           -19
                       -75    -70         -65      -60    -55     -50     -45     -40         -35   -30     -25   -20     -15      -10

                                                         Pi, Input, 2-tone level (dBm/tone)
                                                                                                                                DC4KU
```

**Figure 8: FT-710 - IMD3 history**

```text
            2 x f1-f2                f1                             f1            2 x f2-f1
```

**Figure 9: IMD3 interference signals arising at Pi = -19dBm**

Note on intermodulation: Theoretically, an A/D converter should not produce any intermodulation at all up to its limit (clipping). However, due to quantization errors, an A/D converter generates IM, but its magnitude does not follow any regularity. With "dither" one tries to keep the intermodulation as low as possible. With analog receivers, the intermodulation rises and falls by a factor of 1/3, which means that an IP3 can be calculated, which can be used to define and compare the large signal

immunity of receivers. However, there is no IP3 for digital receivers because the course of the intermodulation cannot be calculated. Most manufacturers have recognized this problem and only specify the sensitivity (MDS) and the phase noise (SBN) for direct-sampling SDRs, but no IMDR3. The only important and decisive factor is that all IMD3 curves up to the limit are always below the residential noise (urban noise) or rural noise line (rural noise) drawn in the diagram (Fig. 10). If this is achieved, the IMD3 interference products are no longer audible/detectable when an antenna is connected (3). The FT-710 meets this requirement.

```text
                      Receiver, Sensitivity           Noise Levels (Power) at 14MHz
```

**Figure 10: Type. External noise in urban areas (Residential, Urban) and in rural residential areas (Rural), Rec.**

ITU-R P.372-7, Radio Noise, ARRL Handbook

### 2nd Order Intermodulation (IMD2, DR2)

The 2nd order intermodulation indicates how high the suppression of the sum signal of two CW signals is. In the example, I use a 2-tone signal (Pi) at f1 = 6.1MHz and f2 = 8.1 MHz and measure the unwanted sum signal at f1 + f2 = 14.2MHz (Table 6). With this measurement, the level of both signals is increased until the IMD2 signal appears above the noise with +3dB, ie the limit sensitivity (MDS) has been reached (DR2 = MDS). The DR2 dynamics (DR2, Dynamic Range 2nd Order) is then

DR2 = Pi - MDS.

f1=6,1MHz

RMS Voltmeter

```text
                                     Pi             FT-710      Audio
   f2=8,1MHz      +
                                                   Receiver
                                    f1+f2                        f1+f2

                                                                          +3dB

                                                                            DC4KU
```

**Figure 11: Measurement setup for IMD2 measurement**

The FT-710 has a DR2 dynamic range of 104dB, with and without a preamplifier.

```text
   Amplifier            MDS                   Pi               DR2
      IPO             -126dBm             -22dBm              104dB
     AMP1             -136dBm             -32dBm              104dB
```

**Table 6: 2nd order dynamics (DR2)**

Settings: f1 =6.1MHz, f2 =8.1MHz, f1+2 =14.2MHz, BW=500Hz

f1 + f2 with +3dB above noise

**Figure 12: DR2 interference signal at Pi = -22dBm, IPO**

Result: The 2nd order dynamics of a good receiver should be >100dB, which the FT-710 achieves. At Pi = -22dBm (S9+51dB) an interference signal of +3dB is generated above the noise floor at 14.2MHz. This results in a DR2 of -22dBm - (-126dBm) = 104dB. With AMP1 activated, the DR2 is -32dBm - (-136dBm) = 104dB. Turning on AMP1 (+10dB) has no effect on the receiver's large signal strength.

### BDR (Blocking Dynamic Range)

The Blocking Dynamic Range of a receiver is reached when an unwanted signal becomes so large that a small signal at a distance of 2...20kHz loses amplitude (S/N) by 1dB.

BDR = Blocking Level - Noise Floor (MDS)

In principle, blocking (desensitization) only occurs with analog, superheterodyne receivers; direct- sampling radios do not have this effect (Figure 13). If the maximum level of an ADC is reached at 0dBFS (full scale), it is almost immediately limited and further reception is no longer possible. This effect is known as "clipping" and usually occurs at around -10dBm with direct sampling SDRs.

-1dB

```text
 Pin                     Blocking                Pin
                                                                 Clipping
                                                                 0dBFS



                             BDR                                 Clipping
                                                                  level

                    Noise                                                   Noise

                                    Pout                                            Pout
```

**Figure 13: Analog blocking (left) and digital clipping (right)**

With the FT-710, however, the blocking process is different. It has a special AGC that prevents the RF level at the input of the ADC from reaching the control limit of 0dBFS. Clipping is therefore not achieved and no warning message appears if the receiver is overloaded, as with the IC-7300 (OVF). Instead, the FT-710 reduces its dynamic range with high signals, similar to an analogue receiver. Yaesu defines the BDR of the FT-710 at a dynamic loss of 1dB. This occurs at an input level of +2dBm (IPO, BW=500Hz, 14.2MHz), which results in a BDR of

BDR = Blocking Level - MDS = +2dBm - (-126dBm) = 128dB

Result: The FT-710 can hardly be overdriven (blocked) and its BDR reaches the vicinity of analog receivers. Hybrid SDRs and superheterodyne receivers can reach a BDR of up to 140dB.

### Noise Power Ratio (NPR)

The intermodulation immunity of a receiver can also be determined using the noise power ratio (NPR) (4). The input of the receiver is no longer connected to CW signals driven, but with white noise of constant power.

```text
      White Noise             9MHz
                                                                   f=9MHz
      Generator              Notchfilter                                                RMS
                                                                  BW=500Hz            Voltmeter
```

0...30dB

```text
                    PNoise                                                    Audio
                                                                    FT710
                                                                   Receiver
                                                          PTOT
                                                                                        +3dB
                              B=1kHz                          MDS=-126dBm/500Hz
  Noiseband: 0....10MHz
                                                                                           DC4KU
```

**Figure 14: NPR measuring station**

The test setup consists of a noise generator (0-10MHz), 9MHz notch filter (BW=1kHz) and an adjustable attenuator. As an example, Figure 15 shows a 0dBm noise spectrum with different noise bandwidths of 50MHz, 100MHz and 200MHz.

Noise-Generator Noise Signal

0dBm

```text
Picture 2:                                 Noise



                                                                                  Analyzer-Noise
```

**Figure 15: Noise signal with 0dBm power at 50MHz, 100MHz and 200MHz noise bandwidth**

The receiver is tuned to the center of the notch filter (8.999640MHz) and receives only the noise floor of the receiver at this point. Subsequently, the noise level (PNoise) is increased until a noise rise of +3dB can be seen in the base of the notch filter as well as on the RMS voltmeter. At this point, the intermodulation generated is equal to the receiver sensitivity (Noise = MDS) and the difference of applied noise power (PTOT) to sensitivity (MDS) is equal to the NPR. For the FT-710, this occurs at a noise level (PTOT) of -7dBm. From this, its NPR is calculated as

NPR = P TOT - BWR - MDS = -7dBm - 10log10MHz/500Hz - (-126dBm) = 76dB

with: PTOT = noise power (related to 10MHz noise bandwidth) BWR (Bandwidth Ratio) = 10log BRF/BIF = 10log 10MHz/500Hz = 43dB MDS = -126dBm

Note: Normally the NPR can be identified by the noticeable increase in noise in the base of the notch filter. However, this is not possible on the FT-710 because its spectral display does not have an "AVERAGE" function. Instead, it only shows a wild wriggling of spectral lines, making it difficult to identify small signals in the noise. The FT-DX10/101 has the same problem. Furthermore, the display

only has 50dB dynamics (standard). Fig. 16 shows the difference between an NPR measurement on the FT-710 (without average) and on the IC-7300 (with average and 80 dB dynamic).

Settings: BW=500Hz, PIO

**Figure 16: NPR measurement on the FT-710 (left) and on the IC-7300 with "average" (right)**

Result: With an NPR of 76dB, the FT-710 is in the range of good SDR receivers. Simple SDRs only achieve 40 to 50dB here. For comparison: FT-DX10: 78dB, IC-7300: 76dB

## Transmitter

### HF Output Power

To measure the HF output power, the transmitter is connected to a spectrum analyzer via a 100 watt dummy load (-50dB output) and the maximum power of a CW signal is determined using this (Fig. 17, 18). The harmonic separation of the second harmonic (2xf) is measured in the same way. Power was supplied via a 13.8V/32A power pack.

TX CW On

```text
       FT-710      RF     Dummy
                                          Spectrum
     Transmitter            Load
                                          Analyzer
                           -50dB
```

**Figure 17: HF power measurement using a CW signal**

Settings: CW 500Hz, RF power 100%, supply 13.8VDC, dummy load 50dB

0,38dBm

Power Calculation: 0,38dBm + 50dB = 50,38dBm = 109Watt PEP

**Figure 18: HF output power at 21.2MHz**

**Table 7 below shows the maximum transmitter RF output power in the individual bands and the**

suppression of the 2nd harmonic.

```text
    Frequency         1.9MHz        3.7MHz            7.1MHz      14.2MHz     21.2MHz     28.2MHz        50MHz
  RF Power, PEP       115.8W        112.9W            110.9W      114.3W      109.1W       109.6W        100.7W
   Suppression
                       68dB           67dB             77dB        76dB        90dB          78dB        72dB
  2nd harmonics
```

**Table 7: RF output power (W) and 2nd harmonic rejection (dB)**

### Intermodulation of the transmitter (TX-IMD)

To measure the intermodulation of the transmitter, connect the microphone input to an AF 2-tone generator (f1=800Hz, f2=1200Hz) (Figure 19) and set the microphone voltage so that the transmitter reaches its maximum output power (PEP). The IMD3 distances can be determined directly from the spectrum of the analyzer (Fig. 20).

f1=800Hz

Audio

```text
                     f1+f2                            60dB
                                 FD-710        RF
                +                                     Dummy       Spectrum
  f2=1200Hz                    Transmitter             Load       Analyzer




                                                                      DC4KU
```

**Figure 19: IMD measurement at the transmitter**

Since the transmitter is driven with two equally large, closely adjacent AF signals, there is a beating in which the signals add up or cancel each other out. With a PEP power of 109 watts, the levels of the two carrier signals are therefore 6 dB below the peak power, at 54.5 watts.

PEP = 109W -6dB, Paverage = 54,5W IMD3 IMD5 Power at 21,2MHz IMD7 Pf1 = 27,25Watt IMD9 Pf2 = 27,25Watt Paverage = 54,5Watt PEP = 109Watt

f1 f2

**Figure 20: Intermodulation of the transmitter at 21.2 MHz: IMD3 = 29.3dB**

Determined IMD3 distances of the transmitter in the individual bands:

```text
   Frequency        1.9MHz        3.7MHz              7.1MHz       14.2MHz      21.2MHz       28.2MHz       50MHz
 IMD3 distance      27.2dBc      28.1dBc             30.0dBc       29.2dBc      29.3dBc       28.3dBc      24.6dBc
```

**Table 8: Transmitter IMD3 results**

The occupied bandwidth and intermodulation of a transmitter can also be determined via a noise signal (5). A low-frequency, white noise band is fed into the microphone input as a modulation signal and the transmitter is adjusted to maximum power. Figure 21 shows the result of the measurements. The almost rectangular block (envelope) in the middle of the spectrum shows the bandwidth of the used SSB filter, dominated by white noise. Theoretically, both flanks should run steeply down to the

background noise, but unfortunately they don't do that in practice. The first IMD products appear at a distance of around 30dBc, the level of which decreases only slowly in the direction of higher and lower frequencies. The achieved IMD-distance at 100 W and 40 W is identical.

IMD=29,3dB

100W

```text
             40W                  Noise

                            Intermodulation
```

**Figure 21: Transmitter noise signal at 100 watts (yellow) and 40 watts (purple), 14.2MHz (SSB)**

Due to the injected noise, individual spectral lines are no longer displayed, but a cumulative spectrum consisting of many IMD products. For this reason, an IMD measurement with noise is much more realistic than with only 2 signals. The procedure, on the other hand, is also harsh and rigorous, similar to the NPR measurement on receivers. It is important that the IMD products to the right and left of the user channel drop off relatively quickly so that adjacent channels are not disturbed.

### Transmitter Sideband Noise (TX SBN, TX Phase Noise)

The sideband noise (composite sideband noise) of a transmitter should be as low as possible so that neighboring, small signals are not disturbed by it (6). A quartz filter (7.07 MHz, BW=2 kHz), spectrum analyzer and terminating resistor (-50dB) are used to measure the TX-SBN (Figure 22). The analyzer is tuned to the center frequency of the filter and the CW signal from the transmitter is set at a distance of 5 to 100kHz from the filter center frequency. At this distance, the transmission signal is strongly suppressed by the edge of the filter and only the noise of the transmitter from 7,070MHz > = +/-2kHz is allowed to pass.

Spectrum Analyzer

```text
                                Chrystal-Filter               Preamplifier: ON
                                 f=7.070MHz
        CW                        BW=2kHz                                  Carrier
                                                         P
                     50dB                                         Filter
                                                  0dBm
      FT-710
    Transmitter
                                                                  SBN
                                                                                     f
  fs=7.070MHz                                                       f        fs
  +2kHz, +5kHz, +10kHz,
  +20kHz, +50kHz, +100kHz
                                                                              DC4KU
```

**Figure 22: Measurement setup for transmitter SBN measurements in the 40m band with a spectrum analyzer**

Because the transmission signal is attenuated by 90dB outside the filter, the analyzer can be set to 0dB attenuation and +20dB pre-amplification and thus achieves a measurement limit of -160dBm/Hz. As an example, Figure 23 shows the measurement of the TX sideband noise at a distance of 5 kHz from the carrier at an output power of 100 watts.

suppressed Carrier

TX-SBN AM-Noise Filter Noise

5kHz

**Figure 23: SBN measurement at 5 kHz offset to the carrier, SBN = -128.4dBc/Hz**

**Table 9 shows the determined SBN of the transmitter at 100 and 50 Watts of power, at distances**

from 2.5 to 100 kHz to the carrier and Figure 24 shows the SBN curve. If the power is reduced to 50 Watt, the SBN increases by about 5 dB.

Transmitted Composite Noise at 100W and 50W

```text
 Offset kHz                 SBN in dBc/Hz        SBN in dBc/Hz
                              100 watts            50 watts
                 2.5            -125                 -120
                  5             -128                 -122
                 10             -129                 -124
                 20             -130                 -125
                 50             -132                 -128
                 100            -135                 -130
```

**Table 9: Cumulative TX-SBN**

Transmitter Sideband Noise -100

-110 SBN (dBc/Hz)

-120 50 W -130 100 W -140

-150

```text
                        0   10   20      30    40     50      60   70     80    90    100
                                               Offset (kHz)                          DC4KU
```

**Figure 24: Course of the TX-SBN with 50 and 100 Watt power**

Note: The TX-SBN consists of phase-noise and amplitude-noise. For the FT-710, AM noise is the strongest component, approximately 15dB above the phase noise, increasing the transmitter's cumulative sideband noise by that amount. In the data sheet, Yaesu specifies a TX phase noise of -143dBc/Hz at a distance of 2 kHz (see Figure 3). This is correct, but it only affects the phase noise. However, the cumulative sideband noise (Phase noise + AM noise) acts at the output of the

transmitter. Accordingly, the SBN of the transmitter is only -125dBc/Hz (100 watts) at a distance of 2.5 kHz and only -130dBc/Hz at a distance of 20 kHz. But both are still good values.

## Characteristic values of transceivers

**Table 10 shows the determined characteristic values of some HF transceivers. When comparing, it**

should be noted that the FT-DX10 is a hybrid transceiver, but the FT-710, IC-705, IC-7300, IC- 7300MK2 and SunSDR2DX are direct-sampling SDRs.

```text
                                         Receiver                                      Transmitter
                     MDS            RMDR                DR3                    IMD3            TX-SBN
                                                                    NPR
                   BW 500Hz       Offset 2kHz       Delta f 2kHz            800/1200Hz       Offset 20kHz
FT-710              -126 dBm         116 dB           107 dB        76 dB     29 dBc          -130 dBc/Hz
FTDX-10             -125 dBm         116 dB           110 dB        78 dB     27 dBc          -132 dBc/Hz
SunSDR2DX           -121 dBm         112 dB           106 dB        76 dB     33 dBc          -142 dBc/Hz
IC-7300             -134 dBm         106 dB            99 dB        76 dB     36 dBc          -127 dBc/Hz
IC-7300MK2          -132 dBm         110 dB            98 dB        77 dB     41 dBc         - 136 dBc/Hz
IC-705              -131 dBm         108 dB            98 dB        76 dB     36 dBc          -131 dBc/Hz
```

**Table 10: Characteristics of various transceivers in the 20m band**

DR3: 3rd-order IMD Dynamic Range RMDR: Reciprocal Mixing Dynamic Range MDS: Minimum Detectable Signal NPR: Noise Power Retio IP3: 3rd-order Intercept Point (analogue TRX) TX-SBN: Transmitter Sideband-Noise

## Summary

The FT-710 is a good HF/50/70 MHz Transceiver with excellent HF data. With the FT-710, Yaesu joins the group of direct-sampling SDRs for the first time and need not fear the comparison. It's an all- round successful transceiver.

I would like to thank "WiMo, Antennen und Elektronik GmbH" for the loan of the FT-710.

Werner Schnorrenberg DC4KU October 30, 2022 Rev. 6/26

## Literature

(1) Unterschiede zwischen analogen und digitalen Empfängern https://dc4ku.darc.de/Unterschiede_zwischen_analogen_und_digitalen_Empfaengern_DC4KU.pdf

(2) Messung SBN von Empfängern und Oszillatoren https://dc4ku.darc.de/Messung-Seitenbandrauschen.pdf

(3) Antennenrauschen im Kurzwellenbereich https://dc4ku.darc.de/Antennenrauschen_im_Kurzwellenbereich.pdf

(4) NPR- und Rauschbandbreite https://dc4ku.darc.de/NPR_und_Rauschbandbreite_DC4KU.pdf

(5) Sender IM-Test mittels Rauschen https://dc4ku.darc.de/Sender_IMD-Test_mit_Rauschen_DC4KU.pdf

(6) Seitenbandrauschen von Sendern https://dc4ku.darc.de/Transmitter-Sideband-Noise_DC4KU.pdf
