import subprocess
import subprocess

def set_fan_speed():
    try:
        # Each part of the command is a separate item in the list
        subprocess.run(['sudo', 'pinctrl', 'FAN_PWM', 'op', 'dl'], check=True)
        print("Fan speed set to max")
    except subprocess.CalledProcessError as e:
        print(f"Failed to set fan speed: {e}")
    except FileNotFoundError:
        print("Error: 'pinctrl' command not found. Are you on a Raspberry Pi 5?")

set_fan_speed()