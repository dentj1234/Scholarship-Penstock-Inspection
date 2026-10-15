# UniFi AP uplink signal setup

The base app logs into the UniFi OS server, reads `/proxy/network/api/s/default/stat/device` every five seconds, and displays each AP's active wireless `uplink.signal` in dBm. It uses the fixed controller address `https://192.168.1.1:11443` and skips TLS certificate verification for this closed network.

Both `install_base.py` and `install_basetest.py` now prompt for the UniFi username and password at startup. The password is hidden while typing, and the installer saves both values in `/etc/basecode/unifi.env` for the service.

## Configure the base Pi

If you are updating an already installed Pi, there is no need to rerun the full installer just to change credentials. Put your UniFi local account credentials in `/etc/basecode/unifi.env`:

```ini
UNIFI_USERNAME=your_username
UNIFI_PASSWORD=your_password
```

For an already installed base Pi, copy the updated `app.py`, `templates/`, and `static/` into `/home/jaydenrobot/BaseCode/`. Install the one Python dependency and create the credentials file:

```sh
sudo apt install -y python3-requests
sudo install -d -m 0750 -o root -g jaydenrobot /etc/basecode
sudo nano /etc/basecode/unifi.env
sudo chown root:jaydenrobot /etc/basecode/unifi.env
sudo chmod 640 /etc/basecode/unifi.env
```

Then run `sudo systemctl edit basecode.service` and add:

```ini
[Service]
EnvironmentFile=-/etc/basecode/unifi.env
```

Apply it and check the journal:

```sh
sudo systemctl daemon-reload
sudo systemctl restart basecode.service
sudo journalctl -u basecode.service -f
```

The signal labels are approximate: `−60 dBm` or stronger is strong, `−61` to `−70 dBm` is marginal, and below `−70 dBm` is weak. Tune any range or turn-back threshold during testing.
