# NTC Temperature / Voltage Calculator — Final Version

`NTC_Temperature_Voltage_Calculator_v4.py` is the standalone desktop simulator for an NTC resistor divider. It calculates the divider response from -50 to 150 °C, routes both measurement nodes through separate amplifiers with a shared gain, and displays voltage or ADC results. V4 also closes all Tk and Matplotlib resources when the window exits.

## Requirements

- Python 3 with Tkinter (included with the standard Windows Python installer)
- Matplotlib and NumPy

On Windows, run `install_requirements.cmd`, or install manually:

```cmd
py -m pip install matplotlib
```

## Run

```cmd
py NTC_Temperature_Voltage_Calculator_v4.py
```

## How to use

1. Enter the circuit values. Resistances are in ohms, beta is in kelvin, and **Gain** applies to both amplifier stages.
2. Select **Calculate** to update the simulation.
3. Choose **Voltage**, **ADC**, or **Both** for the plot y-axis.
4. Hover over the plot to inspect values; click a temperature point to show its two amplifier-output voltages in the output panel.
5. Select **Export CSV** to save the NTC-amplifier output at every whole degree from -50 to 150 °C.

The CSV contains 201 samples with numeric-only data cells: temperature, NTC-amplifier ADC code, and NTC-amplifier voltage. Units appear only in the column headers.

> Amplifier outputs are limited to the configured reference voltage before plotting and ADC conversion.
>
<img width="1138" height="926" alt="Screenshot 2026-08-21 003316" src="https://github.com/user-attachments/assets/412c4fef-fe49-4799-9c58-650cb54804ed" />

