"""Standalone V4 of the NTC temperature/voltage calculator."""

import csv
import math
import os
import sys
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

try:
    import matplotlib
    import numpy as np

    matplotlib.use("TkAgg")

    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    from matplotlib.figure import Figure
except ImportError:
    raise SystemExit(
        "matplotlib is required.\n"
        "Install it with: python -m pip install matplotlib"
    )


COPYRIGHT_NAME = "Developed by KindCircuits @ GitHub - with AI-assisted coding tools "


class NTCVoltageCalculator:
    T_MIN_C = -50.0
    T_MAX_C = 150.0
    POINTS = 401

    def __init__(self, root):
        self.root = root
        self._closing = False
        self.root.title("NTC Voltage Calculator v4")
        self.root.geometry("1150x900")
        self.root.minsize(1000, 800)

        self.vars = {
            "vsource": tk.StringVar(value="3.3"),
            "r1": tk.StringVar(value="10000"),
            "r2": tk.StringVar(value="1"),
            "r25": tk.StringVar(value="100000"),
            "beta": tk.StringVar(value="4100"),
            "vref": tk.StringVar(value="2.5"),
            "gain": tk.StringVar(value="1"),
            "adc_bits": tk.StringVar(value="12"),
        }

        self.axis_mode = tk.StringVar(value="voltage")
        self.node_ntc_r2 = tk.StringVar(value="0.000 V")
        self.node_r2_r1 = tk.StringVar(value="0.000 V")
        self.selected_temperature = tk.StringVar(value="25.00 °C")
        self.cursor_info = tk.StringVar(
            value="Move the mouse over the graph to inspect the curves."
        )

        self._build_ui()
        self.calculate()
        self.root.protocol("WM_DELETE_WINDOW", self.shutdown)

    def _build_ui(self):
        main = ttk.Frame(self.root, padding=12)
        main.pack(fill="both", expand=True)

        left = ttk.Frame(main)
        left.pack(side="left", fill="y", padx=(0, 12))

        right = ttk.Frame(main)
        right.pack(side="right", fill="both", expand=True)

        # Parameters
        params = ttk.LabelFrame(left, text="Circuit Parameters", padding=12)
        params.pack(fill="x")

        rows = [
            ("VSource", "vsource", "V"),
            ("R1", "r1", "Ω"),
            ("R2", "r2", "Ω"),
            ("NTC R25", "r25", "Ω"),
            ("NTC Beta", "beta", "K"),
            ("Reference Voltage", "vref", "V"),
            ("Gain", "gain", "V/V"),
            ("ADC Resolution", "adc_bits", "bits"),
        ]

        for row, (label, key, unit) in enumerate(rows):
            ttk.Label(params, text=label).grid(
                row=row, column=0, sticky="w", padx=(0, 8), pady=5
            )
            entry = ttk.Entry(params, textvariable=self.vars[key], width=16)
            entry.grid(row=row, column=1, sticky="ew", pady=5)
            ttk.Label(params, text=unit).grid(
                row=row, column=2, sticky="w", padx=(6, 0), pady=5
            )

        params.columnconfigure(1, weight=1)

        ttk.Label(
            params,
            text="All resistances are in ohms. Beta is in kelvin.",
            foreground="#555555",
            wraplength=270,
        ).grid(row=len(rows), column=0, columnspan=3, sticky="w", pady=(8, 0))

        # Outputs
        outputs = ttk.LabelFrame(left, text="Calculated Outputs", padding=12)
        outputs.pack(fill="x", pady=(12, 0))

        self._output_row(outputs, 0, "Temperature", self.selected_temperature)
        self._output_row(outputs, 1, "NTC-R2 Amp Out", self.node_ntc_r2)
        self._output_row(outputs, 2, "R2-R1 Amp Out", self.node_r2_r1)

        # Buttons
        buttons = ttk.Frame(left)
        buttons.pack(fill="x", pady=(12, 0))

        ttk.Button(buttons, text="Calculate", command=self.calculate).pack(
            side="left", fill="x", expand=True
        )
        ttk.Button(buttons, text="Reset", command=self.reset).pack(
            side="left", fill="x", expand=True, padx=(8, 0)
        )
        ttk.Button(buttons, text="Export CSV", command=self.export_csv).pack(
            side="left", fill="x", expand=True, padx=(8, 0)
        )

        # Circuit diagram
        diagram = ttk.LabelFrame(left, text="Circuit Diagram", padding=8)
        diagram.pack(fill="x", pady=(12, 0))

        circuit_canvas = tk.Canvas(
            diagram,
            width=300,
            height=190,
            background="white",
            highlightthickness=0,
        )
        circuit_canvas.pack(fill="x")
        self._draw_circuit_diagram(circuit_canvas)

        # Plot
        plot_frame = ttk.LabelFrame(right, text="Temperature vs. Output", padding=8)
        plot_frame.pack(fill="both", expand=True)

        controls = ttk.Frame(plot_frame)
        controls.pack(fill="x", pady=(0, 8))

        ttk.Label(controls, text="Y-axis:").pack(side="left")

        ttk.Radiobutton(
            controls, text="Voltage", value="voltage",
            variable=self.axis_mode, command=self.refresh_plot
        ).pack(side="left", padx=(8, 4))

        ttk.Radiobutton(
            controls, text="ADC", value="adc",
            variable=self.axis_mode, command=self.refresh_plot
        ).pack(side="left", padx=4)

        ttk.Radiobutton(
            controls, text="Both", value="both",
            variable=self.axis_mode, command=self.refresh_plot
        ).pack(side="left", padx=4)

        # Construct the embedded figure directly. pyplot.subplots() creates a
        # separate hidden Tk window that can keep the packaged process alive.
        self.figure = Figure(figsize=(7.2, 5.2), dpi=100)
        self.ax = self.figure.add_subplot(111)
        self.canvas = FigureCanvasTkAgg(self.figure, master=plot_frame)
        self.canvas.get_tk_widget().pack(fill="both", expand=True)

        status = ttk.Label(
            plot_frame,
            textvariable=self.cursor_info,
            anchor="w",
            relief="sunken",
            padding=6
        )
        status.pack(fill="x", pady=(8, 0))

        self._mpl_connections = [
            self.canvas.mpl_connect(
                "motion_notify_event", self.on_mouse_move
            ),
            self.canvas.mpl_connect(
                "button_press_event", self.on_plot_click
            ),
        ]

        self.plot_temps = []
        self.plot_v1 = []
        self.plot_v2 = []
        self.hover_line = None
        self.hover_dot1 = None
        self.hover_dot2 = None

    @staticmethod
    def _draw_resistor(canvas, x, y_top, y_bottom):
        """Draw a compact vertical resistor symbol and its connecting leads."""
        lead = 5
        zigzag = [
            x, y_top,
            x - 8, y_top + lead,
            x + 8, y_top + lead * 2,
            x - 8, y_top + lead * 3,
            x + 8, y_top + lead * 4,
            x - 8, y_top + lead * 5,
            x, y_bottom,
        ]
        canvas.create_line(zigzag, fill="#1f4e79", width=2, joinstyle="round")

    @staticmethod
    def _draw_amplifier(canvas, input_x, center_y, name):
        """Draw a non-inverting amplifier with a shared configurable gain."""
        color = "#7a3e00"
        left = input_x + 45
        right = left + 38
        output = right + 35
        small_font = ("TkDefaultFont", 7)

        canvas.create_line(input_x, center_y, left, center_y, fill=color, width=2)
        canvas.create_polygon(
            left, center_y - 18,
            left, center_y + 18,
            right, center_y,
            fill="#fff7ed",
            outline=color,
            width=2,
        )
        canvas.create_text(left + 8, center_y - 7, text="+", fill=color, font=small_font)
        canvas.create_text(left + 20, center_y + 5, text="Gain", fill=color, font=small_font)
        canvas.create_line(right, center_y, output, center_y, fill=color, width=2)
        canvas.create_oval(output - 3, center_y - 3, output + 3, center_y + 3, fill=color, outline=color)
        canvas.create_text(right + 6, center_y - 13, text=f"{name} OUT", anchor="w", fill=color, font=small_font)

    def _draw_circuit_diagram(self, canvas):
        """Draw the divider plus one shared-gain amplifier per measurement node."""
        wire_color = "#202020"
        part_color = "#1f4e79"
        node_color = "#b24700"
        branch_x = 120
        source_x = 40
        font = ("TkDefaultFont", 8)

        # Voltage source and the top/bottom supply wires.
        canvas.create_oval(
            source_x - 20, 75, source_x + 20, 115,
            outline=part_color, width=2,
        )
        canvas.create_text(source_x, 87, text="+", fill=part_color, font=("TkDefaultFont", 11, "bold"))
        canvas.create_text(source_x, 103, text="−", fill=part_color, font=("TkDefaultFont", 11, "bold"))
        canvas.create_text(source_x, 130, text="VSource", fill=part_color, font=font)
        canvas.create_line(source_x, 75, source_x, 20, branch_x, 20, branch_x, 31, fill=wire_color, width=2)
        canvas.create_line(source_x, 115, source_x, 156, branch_x, 156, fill=wire_color, width=2)

        # Series divider and the two measurement nodes.
        self._draw_resistor(canvas, branch_x, 31, 56)
        canvas.create_line(branch_x, 56, branch_x, 66, fill=wire_color, width=2)
        canvas.create_oval(branch_x - 3, 63, branch_x + 3, 69, fill=node_color, outline=node_color)
        self._draw_resistor(canvas, branch_x, 76, 101)
        canvas.create_line(branch_x, 101, branch_x, 111, fill=wire_color, width=2)
        canvas.create_oval(branch_x - 3, 108, branch_x + 3, 114, fill=node_color, outline=node_color)
        self._draw_resistor(canvas, branch_x, 121, 146)
        canvas.create_line(branch_x, 146, branch_x, 156, fill=wire_color, width=2)

        canvas.create_text(136, 43, text="R1", anchor="w", fill=part_color, font=font)
        canvas.create_text(136, 58, text="R2-R1", anchor="w", fill=node_color, font=font)
        canvas.create_text(136, 88, text="R2", anchor="w", fill=part_color, font=font)
        canvas.create_text(136, 103, text="NTC-R2", anchor="w", fill=node_color, font=font)
        canvas.create_text(136, 133, text="NTC", anchor="w", fill=part_color, font=font)
        self._draw_amplifier(canvas, branch_x, 66, "A1")
        self._draw_amplifier(canvas, branch_x, 111, "A2")

        # Ground reference shared by the NTC and negative source terminal.
        canvas.create_line(branch_x, 156, branch_x, 164, fill=wire_color, width=2)
        canvas.create_line(branch_x - 15, 164, branch_x + 15, 164, fill=wire_color, width=2)
        canvas.create_line(branch_x - 10, 169, branch_x + 10, 169, fill=wire_color, width=2)
        canvas.create_line(branch_x - 5, 174, branch_x + 5, 174, fill=wire_color, width=2)
        canvas.create_text(branch_x + 24, 169, text="GND", anchor="w", fill=wire_color, font=font)
        canvas.create_text(
            225, 177,
            text="A1/A2 use the\nshared Gain setting",
            justify="center",
            fill="#555555",
            font=("TkDefaultFont", 7),
        )

    def _output_row(self, parent, row, label, variable):
        ttk.Label(parent, text=label).grid(
            row=row, column=0, sticky="w", padx=(0, 10), pady=5
        )
        ttk.Label(
            parent,
            textvariable=variable,
            font=("TkDefaultFont", 10, "bold"),
        ).grid(row=row, column=1, sticky="e", pady=5)
        parent.columnconfigure(1, weight=1)

    def _read_float(self, key):
        text = self.vars[key].get().strip().replace(",", ".")
        if not text:
            raise ValueError(f"{key} is empty.")
        return float(text)

    @staticmethod
    def ntc_resistance(r25, beta, temp_c):
        t_k = temp_c + 273.15
        t25_k = 25.0 + 273.15
        return r25 * math.exp(beta * (1.0 / t_k - 1.0 / t25_k))

    @staticmethod
    def fmt_resistance(value_ohm):
        if abs(value_ohm) >= 1_000_000:
            return f"{value_ohm / 1_000_000:.3f} MΩ"
        if abs(value_ohm) >= 1_000:
            return f"{value_ohm / 1_000:.3f} kΩ"
        return f"{value_ohm:.3f} Ω"

    @staticmethod
    def cap_voltage(voltage, vref):
        # Positive-voltage circuit: cap output between 0 V and Vref.
        return max(0.0, min(voltage, vref))

    def calculate(self):
        try:
            vsource = self._read_float("vsource")
            r1 = self._read_float("r1")
            r2 = self._read_float("r2")
            r25 = self._read_float("r25")
            beta = self._read_float("beta")
            vref = self._read_float("vref")
            gain = self._read_float("gain")
            adc_bits_float = self._read_float("adc_bits")

            if adc_bits_float < 1 or not adc_bits_float.is_integer() or adc_bits_float > 32:
                raise ValueError("ADC Resolution must be an integer from 1 to 32 bits.")
            adc_bits = int(adc_bits_float)
            adc_max = (2 ** adc_bits) - 1

            if vsource < 0:
                raise ValueError("VSource must be >= 0 V.")
            if r1 <= 0 or r2 <= 0 or r25 <= 0:
                raise ValueError("R1, R2 and R25 must be > 0.")
            if beta <= 0:
                raise ValueError("Beta must be > 0.")
            if vref < 0:
                raise ValueError("Reference voltage must be >= 0 V.")
            if not math.isfinite(gain) or gain < 0:
                raise ValueError("Gain must be a finite number >= 0.")

            # Calculate at 25 °C for the numeric output boxes.
            r_ntc_25 = r25
            total_25 = r1 + r2 + r_ntc_25
            i25 = vsource / total_25

            v_ntc_r2_25 = self.cap_voltage(i25 * r_ntc_25 * gain, vref)
            v_r2_r1_25 = self.cap_voltage(i25 * (r2 + r_ntc_25) * gain, vref)

            self.selected_temperature.set("25.00 °C")
            self.node_ntc_r2.set(f"{v_ntc_r2_25:.6f} V")
            self.node_r2_r1.set(f"{v_r2_r1_25:.6f} V")

            temps = [
                self.T_MIN_C + (self.T_MAX_C - self.T_MIN_C) * i / (self.POINTS - 1)
                for i in range(self.POINTS)
            ]

            v1 = []
            v2 = []

            for temp_c in temps:
                r_ntc = self.ntc_resistance(r25, beta, temp_c)
                total = r1 + r2 + r_ntc
                current = vsource / total

                node_ntc_r2 = current * r_ntc
                node_r2_r1 = current * (r2 + r_ntc)

                v1.append(self.cap_voltage(node_ntc_r2 * gain, vref))
                v2.append(self.cap_voltage(node_r2_r1 * gain, vref))

            self._update_plot(
                temps, v1, v2, vref, adc_max, adc_bits
            )
            return True

        except (ValueError, OverflowError) as exc:
            messagebox.showerror("Invalid input", str(exc))
            return False
        except Exception as exc:
            messagebox.showerror("Error", f"Unexpected error:\n{exc}")
            return False

    def export_csv(self):
        """Export the NTC amplifier output at each whole-degree sample."""
        if not self.calculate():
            return

        destination = filedialog.asksaveasfilename(
            title="Export NTC Amplifier Data",
            defaultextension=".csv",
            initialfile="ntc_amplifier_data.csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
        )
        if not destination:
            return

        try:
            rows = []
            for temperature, ntc_amplifier_voltage in zip(
                self.plot_temps, self.plot_v1
            ):
                integer_temperature = round(temperature)
                if not math.isclose(temperature, integer_temperature, abs_tol=1e-9):
                    continue

                adc_value = self._voltage_to_adc(
                    ntc_amplifier_voltage, self.plot_vref, self.plot_adc_max
                )
                adc_code = int(math.floor(float(adc_value) + 0.5))
                rows.append(
                    [
                        int(integer_temperature),
                        adc_code,
                        f"{float(ntc_amplifier_voltage):.4f}",
                    ]
                )

            with open(destination, "w", newline="", encoding="utf-8-sig") as csv_file:
                writer = csv.writer(csv_file)
                writer.writerow(
                    [
                        "Temperature (°C)",
                        "NTC Amplifier ADC Code (counts)",
                        "NTC Amplifier Voltage (V)",
                    ]
                )
                writer.writerows(rows)

            messagebox.showinfo(
                "Export complete", f"Exported {len(rows)} rows to:\n{destination}"
            )
        except OSError as exc:
            messagebox.showerror("Export failed", f"Could not write the CSV file:\n{exc}")

    def _voltage_to_adc(self, voltage, vref, adc_max):
        if vref <= 0:
            return 0.0 if np.isscalar(voltage) else np.zeros_like(voltage, dtype=float)
        # Match the capped 0..Vref voltage range.
        value = voltage / vref * adc_max
        return np.clip(value, 0.0, adc_max)

    def _update_plot(self, temps, v_ntc_r2, v_r2_r1, vref, adc_max, adc_bits):
        self.plot_temps = temps
        self.plot_v1 = v_ntc_r2
        self.plot_v2 = v_r2_r1
        self.plot_vref = vref
        self.plot_adc_max = adc_max
        self.plot_adc_bits = adc_bits

        self._redraw_plot()

    def refresh_plot(self):
        if self.plot_temps:
            self._redraw_plot()

    def _redraw_plot(self):
        try:
            vref = self.plot_vref
            adc_max = self.plot_adc_max
            adc_bits = self.plot_adc_bits
        except AttributeError:
            return

        self.ax.clear()

        mode = self.axis_mode.get()

        if mode in ("voltage", "both"):
            self.ax.plot(
                self.plot_temps,
                self.plot_v1,
                linewidth=2,
                label="NTC-R2 Amp Output",
            )
            self.ax.plot(
                self.plot_temps,
                self.plot_v2,
                linewidth=2,
                label="R2-R1 Amp Output",
            )
            self.ax.set_ylabel("Voltage (V)")

        if mode == "adc":
            adc1 = [
                self._voltage_to_adc(v, vref, adc_max)
                for v in self.plot_v1
            ]
            adc2 = [
                self._voltage_to_adc(v, vref, adc_max)
                for v in self.plot_v2
            ]
            self.ax.plot(
                self.plot_temps,
                adc1,
                linewidth=2,
                label="NTC-R2 Amp Output",
            )
            self.ax.plot(
                self.plot_temps,
                adc2,
                linewidth=2,
                label="R2-R1 Amp Output",
            )
            self.ax.set_ylabel(f"ADC Code (0–{adc_max}, {adc_bits}-bit)")
            self.ax.set_ylim(0, max(adc_max, 1) * 1.08)

        elif mode == "both":
            self.ax.set_ylabel("Voltage (V)")
            self.ax.set_ylim(0, max(vref, 0.1) * 1.08)

            secax = self.ax.secondary_yaxis(
                "right",
                functions=(
                    lambda voltage: self._voltage_to_adc(voltage, vref, adc_max),
                    lambda adc: (adc / adc_max * vref) if adc_max else 0.0,
                ),
            )
            secax.set_ylabel(f"ADC Code (0–{adc_max}, {adc_bits}-bit)")
        else:
            self.ax.set_ylim(0, max(vref, 0.1) * 1.08)

        self.ax.set_title("NTC Amplifier Outputs")
        self.ax.set_xlabel("Temperature (°C)")
        self.ax.set_xlim(self.T_MIN_C, self.T_MAX_C)
        self.ax.grid(True, alpha=0.3)
        self.ax.legend()

        self.hover_line = None
        self.hover_dot1 = None
        self.hover_dot2 = None

        self.figure.tight_layout()
        self.canvas.draw_idle()

    def on_mouse_move(self, event):
        if event.inaxes != self.ax or not self.plot_temps:
            if self.cursor_info.get() != "Move the mouse over the graph to inspect the curves.":
                self.cursor_info.set(
                    "Move the mouse over the graph to inspect the curves."
                )
            return

        # Convert mouse X to nearest temperature sample.
        x = event.xdata
        idx = min(
            range(len(self.plot_temps)),
            key=lambda i: abs(self.plot_temps[i] - x)
        )

        temp = self.plot_temps[idx]
        v1 = self.plot_v1[idx]
        v2 = self.plot_v2[idx]

        adc1 = self._voltage_to_adc(v1, self.plot_vref, self.plot_adc_max)
        adc2 = self._voltage_to_adc(v2, self.plot_vref, self.plot_adc_max)

        self.cursor_info.set(
            f"T = {temp:.2f} °C   |   "
            f"NTC-R2 Amp = {v1:.4f} V ({adc1:.1f})   |   "
            f"R2-R1 Amp = {v2:.4f} V ({adc2:.1f})"
        )

        # Vertical guide line and markers.
        if self.hover_line is not None:
            try:
                self.hover_line.remove()
            except ValueError:
                pass

        if self.hover_dot1 is not None:
            try:
                self.hover_dot1.remove()
            except ValueError:
                pass

        if self.hover_dot2 is not None:
            try:
                self.hover_dot2.remove()
            except ValueError:
                pass

        self.hover_line = self.ax.axvline(
            temp, linestyle="--", linewidth=1
        )

        mode = self.axis_mode.get()

        if mode == "adc":
            y1 = adc1
            y2 = adc2
        else:
            y1 = v1
            y2 = v2

        self.hover_dot1, = self.ax.plot(
            temp, y1, marker="o", markersize=6
        )
        self.hover_dot2, = self.ax.plot(
            temp, y2, marker="o", markersize=6
        )

        self.canvas.draw_idle()

    def on_plot_click(self, event):
        """Show the selected plot sample's amplifier outputs in the output panel."""
        if event.inaxes != self.ax or event.xdata is None or not self.plot_temps:
            return

        idx = min(
            range(len(self.plot_temps)),
            key=lambda i: abs(self.plot_temps[i] - event.xdata),
        )
        temp = self.plot_temps[idx]
        v1 = self.plot_v1[idx]
        v2 = self.plot_v2[idx]

        self.node_ntc_r2.set(f"{v1:.6f} V")
        self.node_r2_r1.set(f"{v2:.6f} V")
        self.selected_temperature.set(f"{temp:.2f} °C")
        self.cursor_info.set(
            f"Selected T = {temp:.2f} °C — amplifier outputs updated."
        )

    def shutdown(self):
        """Release all GUI resources and stop the process cleanly."""
        if self._closing:
            return

        self._closing = True

        for connection_id in self._mpl_connections:
            try:
                self.canvas.mpl_disconnect(connection_id)
            except (AttributeError, tk.TclError):
                pass
        self._mpl_connections.clear()

        try:
            idle_draw_id = self.canvas._idle_draw_id
            if idle_draw_id is not None:
                self.canvas.get_tk_widget().after_cancel(idle_draw_id)
                self.canvas._idle_draw_id = None
        except (AttributeError, tk.TclError):
            pass

        try:
            self.figure.clear()
        except (AttributeError, tk.TclError):
            pass

        try:
            self.canvas.get_tk_widget().destroy()
        except (AttributeError, tk.TclError):
            pass

        try:
            self.root.quit()
        except tk.TclError:
            pass

        try:
            self.root.destroy()
        except tk.TclError:
            pass

    def reset(self):
        defaults = {
            "vsource": "3.3",
            "r1": "10000",
            "r2": "1",
            "r25": "100000",
            "beta": "4100",
            "vref": "2.5",
            "gain": "1",
            "adc_bits": "12",
        }
        for key, value in defaults.items():
            self.vars[key].set(value)
        self.calculate()


def main():
    root = tk.Tk()
    try:
        ttk.Style().theme_use("clam")
    except tk.TclError:
        pass

    footer = ttk.Label(
        root,
        text=COPYRIGHT_NAME,
        anchor="center"
    )
    footer.pack(side="bottom", fill="x", padx=12, pady=(0, 8))

    app = NTCVoltageCalculator(root)

    try:
        root.mainloop()
    finally:
        app.shutdown()

    return 0


if __name__ == "__main__":
    exit_code = main()

    # The UI has already completed orderly cleanup. In a frozen GUI build,
    # bypass third-party interpreter shutdown hooks so no process can linger.
    if getattr(sys, "frozen", False):
        os._exit(exit_code)

    raise SystemExit(exit_code)


