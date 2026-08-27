#!/usr/bin/env python3
import os
import sys
import subprocess
import urllib.request

if os.geteuid() != 0:
    print("❌ Error: Must be run as root! Use: sudo python3 install_node.py")
    sys.exit(1)

def run_cmd(cmd):
    print(f"--> {cmd}")
    subprocess.run(cmd, shell=True, check=True)

print("--- 🤖 Setting Up Penstock Node Pi ---")

# -------------------------------------------------------------------
# 1. Select Node Index & Setup Parameters
# -------------------------------------------------------------------
node_idx = input("Enter Node Index (0 for End Robot [192.168.1.2], 1 for Middle Relay [192.168.1.3]): ").strip()

if node_idx == "0":
    node_ip = "192.168.1.2"
    node_name = "End Robot"
elif node_idx == "1":
    node_ip = "192.168.1.3"
    node_name = "Middle Relay"
else:
    print("❌ Invalid node index selected! Must be 0 or 1.")
    sys.exit(1)

print(f"Configuring as Node {node_idx} ({node_name}) with IP {node_ip}...")

# -------------------------------------------------------------------
# 2. ALL ONLINE OPERATIONS (Apt & Web Downloads)
# -------------------------------------------------------------------
print("\n[Step 1/5] Installing Base Packages via apt...")
run_cmd("apt update && apt install -y wget tar libcamera-dev libfreetype6 python3-pip python3-socketio-client network-manager")

print("\n[Step 2/5] Downloading MediaMTX binary...")
mediamtx_ver = "v1.12.3"
install_dir = "/opt/mediamtx"
tar_file = f"mediamtx_{mediamtx_ver}_linux_arm64.tar.gz"
download_url = f"https://github.com/bluenviron/mediamtx/releases/download/{mediamtx_ver}/{tar_file}"

installer_path = f"/tmp/{tar_file}"
req = urllib.request.Request(
    download_url, 
    headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
)

with urllib.request.urlopen(req) as response, open(installer_path, 'wb') as out_file:
    out_file.write(response.read())

os.makedirs(install_dir, exist_ok=True)
run_cmd(f"tar -xzvf {installer_path} -C {install_dir}")
if os.path.exists(installer_path):
    os.remove(installer_path)

# -------------------------------------------------------------------
# 3. LOCAL CONFIGURATIONS & SERVICE FILE GENERATION
# -------------------------------------------------------------------
print("\n[Step 3/5] Creating service configs and directories...")

# MediaMTX Configuration
mediamtx_conf = """paths:
  cam1:
    source: rpiCamera
    sourceOnDemand: yes
    rpiCameraWidth: 1280
    rpiCameraHeight: 720
    rpiCameraFPS: 30
    rpiCameraBitrate: 3000000
    rpiCameraExposure: normal
    rpiCameraMetering: matrix
  all_others:
"""
with open(f"{install_dir}/mediamtx.yml", "w") as f:
    f.write(mediamtx_conf)

# MediaMTX Systemd Service
mediamtx_service_content = f"""[Unit]
Description=MediaMTX Realtime Media Server
After=network-online.target
Wants=network-online.target

[Service]
User=root
WorkingDirectory={install_dir}
ExecStart={install_dir}/mediamtx {install_dir}/mediamtx.yml
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
"""
with open("/etc/systemd/system/mediamtx.service", "w") as f:
    f.write(mediamtx_service_content)

# Node Code Directory Setup
node_dir = "/home/jaydenrobot/NodeCode"
os.makedirs(node_dir, exist_ok=True)
subprocess.run(["chown", "-R", "jaydenrobot:jaydenrobot", node_dir], check=True)
subprocess.run(["chmod", "-R", "775", node_dir], check=True)

main_script = f"{node_dir}/node_daemon.py"

# Node Code Systemd Service
node_service_content = f"""[Unit]
Description=Robot Node Code Service
After=network-online.target mediamtx.service
Wants=network-online.target mediamtx.service

[Service]
User=jaydenrobot
Group=jaydenrobot
WorkingDirectory={node_dir}
ExecStart=/usr/bin/python3 {main_script}
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
"""
with open("/etc/systemd/system/node_code.service", "w") as f:
    f.write(node_service_content)

# Fan Control
print("Setting fan speed to max...")
try:
    run_cmd("pinctrl FAN_PWM op dl")
except Exception as e:
    print(f"Warning setting fan PWM: {e}")

# Clean up conflicting netplan file if it exists
if os.path.exists("/etc/netplan/50-cloud-init.yaml"):
    try:
        os.remove("/etc/netplan/50-cloud-init.yaml")
    except Exception:
        pass

# -------------------------------------------------------------------
# 4. NETWORK RECONFIGURATION (NetworkManager / nmcli)
# -------------------------------------------------------------------
print("\n[Step 4/5] Applying Static IP Network Configuration via NetworkManager...")

try:
    run_cmd("ip link set eth0 up")
    
    # Clean up existing static connection if running multiple times
    subprocess.run("nmcli connection delete eth0-static", shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    # Configure eth0 static connection natively
    run_cmd(f"nmcli con add type ethernet con-name eth0-static ifname eth0 ip4 {node_ip}/24")
    run_cmd("nmcli con modify eth0-static ipv4.gateway 192.168.1.1")
    run_cmd("nmcli con modify eth0-static ipv4.dns '192.168.1.1 1.1.1.1'")
    run_cmd("nmcli con modify eth0-static connection.autoconnect yes")
    run_cmd("nmcli con up eth0-static")
    
    print(f"✅ Persistent Static IP {node_ip} configured for eth0!")
except Exception as e:
    print(f"Warning configuring eth0 via nmcli: {e}")

# -------------------------------------------------------------------
# 5. START SERVICES
# -------------------------------------------------------------------
print("\n[Step 5/5] Enabling and Starting Services...")
run_cmd("systemctl daemon-reload")
run_cmd("systemctl enable mediamtx.service")
run_cmd("systemctl start mediamtx.service")
run_cmd("systemctl enable node_code.service")
run_cmd("systemctl start node_code.service")

print("\n✅ Node Setup Finished Successfully!")
print(f"Assigned Static IP: {node_ip}")
print(f"Place your node code script in: {node_dir}/node_daemon.py")