### Real-Time Copy-Paste Between Windows & Linux VM

Universal installer with GUI & live chat for real-time copy-paste between Windows and Linux/VM environments.

Works with Python, Netcat (`nc`), and optionally Pillow for GUI backgrounds.


## Features

* Real-time bidirectional clipboard/text sync between host and VM.
* Cross-platform: works on Windows and Linux (linux not tested yet)
* GUI interface with resizable, gradient/background visuals (requires Pillow).
* Live chat window for typing directly to the VM.
* Automatic IP detection.
* Console fallback if Tkinter GUI is unavailable.
* Easy setup via Python scripts and Netcat.

---

## Requirements

* Python 3.x (tested with 3.14)
* Tkinter (for GUI)
* Pillow (optional, for background image)
* Netcat (`nc`) on the VM side

---

## Installation & Usage

### Windows Host

1. Run `auto_installer.py` using Python:

```powershell
python auto_installer.py
```

2. Enter your VM’s IP and port (default: 4444).
3. Click **Start Installation**.
4. On the VM, run the Netcat command as prompted:

```bash
nc -l [VM_IP] 4444 > vm_server.py
```

5. Once file transfer completes, run:

```bash
python vm_server.py
```

6. Back on Windows, click **Open Chat** to start live communication.

---

### Linux / VM

1. Run `auto_installer.py`.
2. Click **Create Server File** to generate `vm_server.py`.
3. Give your IP to the Windows host.
4. Click **Run Server** to start listening for incoming connection.
5. Windows host can then type directly via GUI chat.

---

## File Structure

* `auto_installer.py` – Main installer with GUI and console fallback.
* `vm_server.py` – Generated server script for VM.
* `.venv/windows_client.ps1` – Generated Windows PowerShell client.
* Optional background images: `rass_wajih.jpg`, `background.jpg`, `bg.png`, etc.

---

## Troubleshooting

* **GUI not loading:** Tkinter not installed → fallbacks to console mode.
* **Pillow errors:** Install manually with:

```bash
pip install Pillow
```

* **Firewall/port issues:** Ensure port 4444 (or custom port) is open on both host and VM.
* **Connection fails:** Verify VM is reachable via ping and Netcat is installed.

---

## Notes

* Tested with Windows 10/11 host and Linux VMs.
* Designed for **real-time text interaction**, not full file sync.
* Works over local network (LAN). Port forwarding needed for remote access.
* Use **Ctrl+C** to stop server on VM terminal.

---

## License
This project is open source under the MIT License.  
You are free to use, modify, and distribute it.  
© 2025 mouones
