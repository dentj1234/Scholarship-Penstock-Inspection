#!/usr/bin/env python3
import os
import sys
import subprocess
import urllib.request

if os.geteuid() != 0:
    print("❌ Error: Must be run as root! Use: sudo python3 install_base.py")
    sys.exit(1)

def run_cmd(cmd):
    print(f"--> {cmd}")
    subprocess.run(cmd, shell=True, check=True)

print("--- 🛰️ Setting Up Base Station Pi ---")

# 1. Enable IP forwarding
print("Enabling IP Forwarding...")
run_cmd("sysctl net.ipv4.ip_forward=1")
run_cmd("sysctl net.ipv6.conf.all.forwarding=1")

# Make IP forwarding permanent across reboots
with open("/etc/sysctl.d/99-ipforward.conf", "w") as f:
    f.write("net.ipv4.ip_forward=1\nnet.ipv6.conf.all.forwarding=1\n")

# 2. Install DHCP Server, Podman, Pip, Flask, Tcpdump
print("Installing Base Packages...")
run_cmd("apt update && apt install -y isc-dhcp-server podman tcpdump python3-pip python3-flask wget")

# 3. Configure /etc/dhcp/dhcpd.conf
print("Configuring dhcpd.conf...")
dhcp_conf = """
subnet 192.168.1.0 netmask 255.255.255.0 {
	range 192.168.1.2 192.168.1.50;
	option routers 192.168.1.1;
}
"""
with open("/etc/dhcp/dhcpd.conf", "a") as f:
    f.write(dhcp_conf)

# 4. Assign Netplan Static IP
print("Configuring Netplan...")
netplan_content = """network:
	version: 2
	ethernets:
		eth0:
			dhcp4: false
			addresses:
				- 192.168.1.1/24
			routes:
				- to: default
				  via: 192.168.1.1
"""
os.makedirs("/etc/netplan", exist_ok=True)
with open("/etc/netplan/50-cloud-init.yaml", "w") as f:
    f.write(netplan_content)

# Apply netplan
try:
    run_cmd("netplan apply")
except Exception as e:
    print(f"Warning running netplan apply: {e}")

# 5. Assign Interface for DHCP
print("Assigning interface for DHCP...")
with open("/etc/default/isc-dhcp-server", "w") as f:
    f.write('INTERFACESv4="eth0"\nINTERFACESv6=""\n')

# 6. Add 5 second delay to startup of dhcp server
print("Adding 5s startup override to isc-dhcp-server...")
os.makedirs("/etc/systemd/system/isc-dhcp-server.service.d/", exist_ok=True)
override_conf = """[Service]
Restart=on-failure
RestartSec=5s
ExecStartPre=/bin/sleep 5
"""
with open("/etc/systemd/system/isc-dhcp-server.service.d/override.conf", "w") as f:
    f.write(override_conf)

# Enable and start DHCP
run_cmd("systemctl daemon-reload")
run_cmd("systemctl enable isc-dhcp-server")

# 7. Increase fan speed to max
print("Setting fan speed to max...")
try:
    run_cmd("pinctrl FAN_PWM op dl")
except Exception as e:
    print(f"Warning setting fan PWM: {e}")

# 8. Setup Base Station Python Script & Service
base_dir = "/home/jaydenrobot/base"
os.makedirs(base_dir, exist_ok=True)

# Example placeholder script (Replace content or overwrite base_script.py directly)
base_script_path = f"{base_dir}/base_script.py"
if not os.path.exists(base_script_path):
    with open(base_script_path, "w") as f:
        f.write("#!/usr/bin/env python3\nprint('Base Station script running...')\n")
    run_cmd(f"chmod +x {base_script_path}")

print("Creating basecode.service...")
base_service_content = f"""[Unit]
Description=Base Station Main Service
After=network-online.target
Wants=network-online.target

[Service]
User=root
Group=root
WorkingDirectory={base_dir}
ExecStart=/usr/bin/python3 {base_script_path}
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
"""
with open("/etc/systemd/system/basecode.service", "w") as f:
    f.write(base_service_content)

run_cmd("systemctl daemon-reload")
run_cmd("systemctl enable basecode.service")

# 9. Install UniFi OS Server
print("\n--- Install UniFi OS Server ---")
unifi_url = input("Paste the UniFi OS Server Linux (arm64) download link from ui.com (or press Enter to skip): ").strip()

if unifi_url:
    installer_path = "/tmp/unifi_os_installer"
    print("Downloading installer...")
    urllib.request.urlretrieve(unifi_url, installer_path)
    run_cmd(f"chmod +x {installer_path}")
    print("Running UniFi OS Server installer...")
    run_cmd(f"{installer_path}")
    if os.path.exists(installer_path):
        os.remove(installer_path)

print("\n✅ Base Station Setup Finished!")
print(f"Place your python script in: {base_dir}/base_script.py")