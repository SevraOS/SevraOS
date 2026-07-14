#!/usr/bin/env python3
import time
import math
import random
import sys

def get_ecg_ascii(val):
    # Map a float -0.3 to 1.0 to a text line representing height
    width = 40
    # normalize -0.3..1.0 to 0..1.0
    norm = (val + 0.3) / 1.3
    idx = int(norm * (width - 1))
    idx = max(0, min(width - 1, idx))
    
    line = [" "] * width
    line[idx] = "●"
    return "".join(line)

def main():
    print("==================================================")
    print("          SevraOS Patient Telemetry Simulator     ")
    print("==================================================")
    print("Press Ctrl+C to terminate the simulation.\n")
    
    # Baseline patient vitals
    hr = 105
    spo2 = 97.2
    temp = 35.8
    bp_sys = 160
    bp_dia = 95
    
    tick = 0
    
    try:
        while True:
            tick += 1
            
            # Periodically drift baseline parameters
            if tick % 10 == 0:
                hr += random.choice([-2, -1, 0, 1, 2])
                hr = max(60, min(140, hr))
                
                spo2 += random.choice([-0.2, -0.1, 0.0, 0.1, 0.2])
                spo2 = max(85.0, min(100.0, spo2))
                
                bp_sys = int(140 + hr * 0.15 + random.randint(-4, 4))
                bp_dia = int(80 + hr * 0.1 + random.randint(-3, 3))
                
                temp = round(35.5 + random.random() * 0.6, 1)

            # Generate real-time ECG waveform value (PQRST complex)
            cycle_pos = (tick % 20) / 20.0
            ecg_val = 0.0
            if cycle_pos < 0.1:   # P Wave
                ecg_val = math.sin(cycle_pos * 10 * math.PI) * 0.15
            elif cycle_pos >= 0.15 and cycle_pos < 0.18: # Q Wave
                ecg_val = -0.1
            elif cycle_pos >= 0.18 and cycle_pos < 0.22: # R Wave (Tall Spike)
                ecg_val = 1.0
            elif cycle_pos >= 0.22 and cycle_pos < 0.25: # S Wave
                ecg_val = -0.25
            elif cycle_pos >= 0.3 and cycle_pos < 0.45:  # T Wave
                ecg_val = math.sin((cycle_pos - 0.3) * (1.0/0.15) * math.pi) * 0.25
                
            # Render live scrolling monitor display
            sys.stdout.write(f"\r[Telemetry] HR: {hr} bpm | BP: {bp_sys}/{bp_dia} mmHg | SpO2: {spo2:.1f}% | Temp: {temp}°C | wave: {get_ecg_ascii(ecg_val)}")
            sys.stdout.flush()
            
            time.sleep(0.08) # ~12.5 Hz refresh rate for smooth display
            
    except KeyboardInterrupt:
        print("\n\nTelemetry simulation ended.")

if __name__ == "__main__":
    main()
