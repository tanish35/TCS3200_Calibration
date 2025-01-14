import time
import pyfirmata
from pyfirmata import Arduino, util
import sys
from statistics import mean

class ColorSensor:
    def __init__(self, port='/dev/tty.usbserial-1130'):
        try:
            print(f"Attempting to connect to Arduino on port {port}...")
            self.board = Arduino(port)
            print("Successfully connected to Arduino Nano")
            
            print("Starting iterator thread...")
            it = util.Iterator(self.board)
            it.start()
            
            print("Configuring TCS3200 pins...")
            self.s0 = self.board.digital[4]
            self.s1 = self.board.digital[5]
            self.s2 = self.board.digital[6]
            self.s3 = self.board.digital[7]
            self.out = self.board.digital[8]
            
            #Gotta chnage this to get it to work
            self.s0.write(1)
            self.s1.write(0)
            
            self.out.mode = pyfirmata.INPUT
            
            
            self.color_signatures = {
                'red': None,
                'green': None,
                'blue': None
            }
            
        
            self.white_reference = None
            
            print("Waiting for sensor stabilization...")
            time.sleep(1.0)
            print("Initialization complete")
            
        except Exception as e:
            print(f"Error during initialization: {str(e)}")
            raise

    def get_raw_reading(self, color_filter):
        self.s2.write(color_filter[0])
        self.s3.write(color_filter[1])
        time.sleep(0.1)
        
        timeout = time.time() + 0.5
        while not self.out.read():
            if time.time() > timeout:
                return 0
        start = time.time()
        
        timeout = time.time() + 0.5
        while self.out.read():
            if time.time() > timeout:
                return 0
        end = time.time()
        
        if end > start:
            return 1.0 / (end - start)
        return 0

    def get_normalized_reading(self):
        readings = {
            'red': [],
            'green': [],
            'blue': []
        }
        
       
        for _ in range(10):
            readings['red'].append(self.get_raw_reading((0, 0)))    
            readings['green'].append(self.get_raw_reading((1, 1)))  
            readings['blue'].append(self.get_raw_reading((0, 1)))   
        
       
        avg_readings = {
            'red': mean(readings['red']),
            'green': mean(readings['green']),
            'blue': mean(readings['blue'])
        }
        
       
        total = sum(avg_readings.values())
        if total == 0:
            return {'red': 0, 'green': 0, 'blue': 0}
            
        return {
            'red': avg_readings['red'] / total,
            'green': avg_readings['green'] / total,
            'blue': avg_readings['blue'] / total
        }

    def white_balance(self):
        print("\nPlace WHITE reference under the sensor")
        input("Press Enter when ready...")
        print("Calibrating white balance...")
        
        self.white_reference = self.get_normalized_reading()
        print("\nWhite balance reference values:")
        for color, value in self.white_reference.items():
            print(f"{color}: {value:.3f}")

    def calibrate(self):
        """Competition-grade calibration process"""
        print("\nStarting color calibration process...")
        
        self.white_balance()
        
        for color in ['red', 'green', 'blue']:
            print(f"\nPlace {color.upper()} reference under the sensor")
            input("Press Enter when ready...")
            print(f"Calibrating {color}...")
            
            reading = self.get_normalized_reading()
            balanced_reading = {
                channel: value / self.white_reference[channel]
                for channel, value in reading.items()
            }
            
            self.color_signatures[color] = balanced_reading
            
            print(f"\n{color.upper()} signature (white-balanced ratios):")
            for channel, value in balanced_reading.items():
                print(f"{channel}: {value:.3f}")
        
        print("\nCalibration complete!")

    def match_color(self, reading):
        def cosine_similarity(v1, v2):
            dot_product = sum(v1[k] * v2[k] for k in v1)
            norm1 = sum(v * v for v in v1.values()) ** 0.5
            norm2 = sum(v * v for v in v2.values()) ** 0.5
            return dot_product / (norm1 * norm2) if norm1 * norm2 > 0 else 0
        
        balanced_reading = {
            channel: value / self.white_reference[channel]
            for channel, value in reading.items()
        }
        
        similarities = {
            color: cosine_similarity(balanced_reading, signature)
            for color, signature in self.color_signatures.items()
        }
        
        best_match = max(similarities.items(), key=lambda x: x[1])
        
        if best_match[1] >= 0.85:
            return best_match[0].capitalize()
        return "Unknown"

    def detect_color(self):
        """Detect color using competition-grade algorithm"""
        try:
            reading = self.get_normalized_reading()
            
            print("\nNormalized ratios:")
            for color, value in reading.items():
                print(f"{color}: {value:.3f}")
            
            return self.match_color(reading)
                
        except Exception as e:
            print(f"Error detecting color: {str(e)}")
            return "Error"

    def run(self):
        print("Starting color sensor. Press CTRL+C to stop.")
        try:
            self.calibrate()
            
            while True:
                color = self.detect_color()
                print(f"Detected color: {color}")
                time.sleep(0.5)
        except KeyboardInterrupt:
            print("\nStopping sensor and cleaning up...")
        finally:
            self.board.exit()
            print("Cleanup complete.")

if __name__ == "__main__":
    try:
        from serial.tools import list_ports
        print("Available ports:")
        for port in list_ports.comports():
            print(f"  - {port.device}")
    except ImportError:
        print("Cannot list ports - pyserial not installed")

    PORT = '/dev/tty.usbserial-1130' 
    
    try:
        sensor = ColorSensor(PORT)
        sensor.run()
    except KeyboardInterrupt:
        print("\nProgram stopped by user")
    except Exception as e:
        print(f"Fatal error: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        if 'sensor' in locals():
            try:
                sensor.board.exit()
            except:
                pass