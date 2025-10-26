#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
auto_installer.py - Universal Installer with GUI & Live Chat
Real-Time Copy-Paste Tool
Works on both Windows and Linux with simple UI
"""

import os
import sys
import socket
import subprocess
import platform
import time
import threading

try:
    import tkinter as tk
    from tkinter import ttk, scrolledtext, messagebox

    HAS_GUI = True
except ImportError:
    HAS_GUI = False

# Check and install Pillow if needed
HAS_PIL = False
try:
    from PIL import Image, ImageTk, ImageDraw, ImageFont

    HAS_PIL = True
except ImportError:
    if HAS_GUI:
        print("\n" + "=" * 60)
        print("Pillow (PIL) is not installed.")
        print("Pillow is needed for the background image feature.")
        print("=" * 60)
        choice = input("\nDo you want to install Pillow now? (yes/no/skip): ").strip().lower()

        if choice in ['yes', 'y']:
            print("\nInstalling Pillow...")
            try:
                subprocess.check_call([sys.executable, "-m", "pip", "install", "Pillow"])
                print("✓ Pillow installed successfully!")
                print("Please restart the application to use the background feature.\n")
                from PIL import Image, ImageTk, ImageDraw, ImageFont

                HAS_PIL = True
            except Exception as e:
                print(f"✗ Failed to install Pillow: {e}")
                print("The application will run without background image.\n")
                HAS_PIL = False
        elif choice == 'skip':
            print("\nSkipping Pillow installation.")
            print("The application will run without background image.\n")
            HAS_PIL = False
        else:
            print("\nPillow installation cancelled.")
            print("The application will run without background image.\n")
            HAS_PIL = False

# ============================================
# FILE TEMPLATES
# ============================================

VM_SERVER_CODE = """# vm_server.py
# Run this on the VM - Python 2.2.6 compatible
# Real-time bidirectional clipboard sync server

import socket
import sys
import select

HOST = '0.0.0.0'
PORT = 4444

def main():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind((HOST, PORT))
    s.listen(1)

    print 'Waiting for connection on %s:%d...' % (HOST, PORT)
    conn, addr = s.accept()
    print 'Connected from', addr
    print 'Type anything and press Enter to send to Windows.'
    print 'Incoming text from Windows will appear automatically.\\n'

    try:
        while True:
            readable, _, _ = select.select([conn, sys.stdin], [], [], 0.1)

            for r in readable:
                if r is conn:
                    data = conn.recv(4096)
                    if not data:
                        print '\\nConnection closed by Windows host.'
                        return
                    sys.stdout.write(data)
                    sys.stdout.flush()

                elif r is sys.stdin:
                    line = sys.stdin.readline()
                    if not line:
                        return
                    conn.sendall(line)

    except KeyboardInterrupt:
        print '\\nShutting down.'
    except Exception, e:
        print 'Error:', e
    finally:
        try:
            conn.close()
            s.close()
        except:
            pass

if __name__ == '__main__':
    main()
"""


def get_windows_client_code(vm_ip, port):
    return f"""# windows_client.ps1
# Real-time bidirectional clipboard sync client

$ip = "{vm_ip}"
$port = {port}

Write-Host "Connecting to VM at $ip`:$port..." -ForegroundColor Green

try {{
    $client = New-Object System.Net.Sockets.TcpClient($ip, $port)
    $stream = $client.GetStream()
    $reader = New-Object System.IO.StreamReader($stream)
    $writer = New-Object System.IO.StreamWriter($stream)
    $writer.AutoFlush = $true

    Write-Host "Connected! Type anything and press Enter to send to VM." -ForegroundColor Green
    Write-Host "Incoming text from VM will appear automatically.`n" -ForegroundColor Cyan

    $receiveJob = Start-Job -ScriptBlock {{
        param($stream)
        $reader = New-Object System.IO.StreamReader($stream)
        try {{
            while ($true) {{
                $line = $reader.ReadLine()
                if ($line -eq $null) {{ break }}
                Write-Output $line
            }}
        }} catch {{}}
    }} -ArgumentList $stream

    while ($true) {{
        if ($receiveJob.HasMoreData) {{
            Receive-Job $receiveJob | ForEach-Object {{
                Write-Host "[VM] $_" -ForegroundColor Cyan
            }}
        }}

        if ([Console]::KeyAvailable) {{
            $line = [Console]::ReadLine()
            if ($line -eq $null) {{ break }}
            $writer.WriteLine($line)
        }}

        Start-Sleep -Milliseconds 50
    }}
}} catch {{
    Write-Host "`nError: $_" -ForegroundColor Red
}} finally {{
    if ($receiveJob) {{
        Stop-Job $receiveJob -ErrorAction SilentlyContinue
        Remove-Job $receiveJob -ErrorAction SilentlyContinue
    }}
    if ($writer) {{ $writer.Close() }}
    if ($reader) {{ $reader.Close() }}
    if ($stream) {{ $stream.Close() }}
    if ($client) {{ $client.Close() }}
    Write-Host "Connection closed." -ForegroundColor Yellow
}}
"""


# ============================================
# UTILITY FUNCTIONS
# ============================================

def get_local_ip():
    """Get local IP address"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "127.0.0.1"


def create_vm_server():
    """Create vm_server.py"""
    with open('vm_server.py', 'w') as f:
        f.write(VM_SERVER_CODE)
    if os.name != 'nt':
        os.chmod('vm_server.py', 0o755)
    return True


def create_windows_client(vm_ip, port):
    """Create windows_client.ps1"""
    os.makedirs('.venv', exist_ok=True)
    with open('.venv/windows_client.ps1', 'w') as f:
        f.write(get_windows_client_code(vm_ip, port))
    return True


def send_file_to_vm(vm_ip, port, filename):
    """Send file to VM via TCP"""
    try:
        with open(filename, 'rb') as f:
            content = f.read()

        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(10)
        sock.connect((vm_ip, port))
        sock.sendall(content)
        sock.close()
        return True, "Success"
    except Exception as e:
        return False, str(e)


def create_gradient_background(width, height):
    """Create background from image, focusing on bottom 50%"""
    background_files = ['rass_wajih.jpg', 'background.jpg', 'background.png', 'bg.jpg', 'bg.png']

    for bg_file in background_files:
        if os.path.exists(bg_file):
            try:
                print(f"Loading background image: {bg_file}")
                img = Image.open(bg_file)

                if img.mode != 'RGB':
                    img = img.convert('RGB')

                img_width, img_height = img.size
                print(f"Image size: {img_width}x{img_height}")

                # Focus on bottom 50% of image for portrait images
                if img_height > img_width * 1.3:  # Portrait orientation
                    # Crop to bottom 60%
                    crop_start = int(img_height * 0.4)
                    img = img.crop((0, crop_start, img_width, img_height))
                    img_width, img_height = img.size

                # Get edge colors for filling
                edge_colors = []
                step = max(1, img.width // 20)
                for x in range(0, img.width, step):
                    edge_colors.append(img.getpixel((x, 0)))
                    edge_colors.append(img.getpixel((x, img.height - 1)))
                for y in range(0, img.height, step):
                    edge_colors.append(img.getpixel((0, y)))
                    edge_colors.append(img.getpixel((img.width - 1, y)))

                avg_r = sum(c[0] for c in edge_colors) // len(edge_colors)
                avg_g = sum(c[1] for c in edge_colors) // len(edge_colors)
                avg_b = sum(c[2] for c in edge_colors) // len(edge_colors)
                bg_color = (avg_r, avg_g, avg_b)

                # Calculate scaling
                img_aspect = img_width / img_height
                window_aspect = width / height

                if window_aspect > img_aspect:
                    new_height = height
                    new_width = int(height * img_aspect)
                else:
                    new_width = width
                    new_height = int(width / img_aspect)

                img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)

                canvas = Image.new('RGB', (width, height), bg_color)

                x_offset = (width - new_width) // 2
                y_offset = (height - new_height) // 2

                canvas.paste(img, (x_offset, y_offset))

                print(f"✓ Background loaded from {bg_file}")
                return canvas
            except Exception as e:
                print(f"✗ Failed to load {bg_file}: {e}")
                continue

    # Fallback gradient
    print("No background image found, using gradient")
    image = Image.new('RGB', (width, height))
    draw = ImageDraw.Draw(image)

    for y in range(height):
        ratio = y / height
        r = int(44 + (52 - 44) * ratio)
        g = int(62 + (152 - 62) * ratio)
        b = int(80 + (219 - 80) * ratio)
        draw.line([(0, y), (width, y)], fill=(r, g, b))

    return image


# ============================================
# LIVE CHAT CLIENT
# ============================================

class LiveChatClient:
    """Live chat client"""

    def __init__(self, parent, vm_ip, port, on_close_callback):
        self.parent = parent
        self.vm_ip = vm_ip
        self.port = port
        self.on_close_callback = on_close_callback
        self.connected = False
        self.sock = None
        self.reader_thread = None
        self.running = False

        self.window = tk.Toplevel(parent)
        self.window.title(f"Live Chat - {vm_ip}:{port} | by mouones (vibecoding)")
        self.window.geometry("700x600")
        self.window.minsize(500, 400)
        self.window.protocol("WM_DELETE_WINDOW", self.close)

        self.create_widgets()
        self.connect()

    def create_widgets(self):
        """Create chat interface"""
        status_frame = tk.Frame(self.window, bg="#27ae60", height=40)
        status_frame.pack(fill=tk.X, side=tk.TOP)
        status_frame.pack_propagate(False)

        self.status_label = tk.Label(status_frame, text="Connecting...",
                                     font=("Arial", 11, "bold"), fg="white", bg="#27ae60")
        self.status_label.pack(pady=10)

        main_container = tk.Frame(self.window)
        main_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        chat_frame = tk.Frame(main_container)
        chat_frame.pack(fill=tk.BOTH, expand=True, side=tk.TOP)

        tk.Label(chat_frame, text="Conversation", font=("Arial", 10, "bold")).pack(anchor=tk.W)

        self.chat_display = scrolledtext.ScrolledText(chat_frame,
                                                      font=("Consolas", 10),
                                                      bg="#ecf0f1", fg="#2c3e50",
                                                      wrap=tk.WORD, state=tk.DISABLED)
        self.chat_display.pack(fill=tk.BOTH, expand=True, pady=5)

        self.chat_display.tag_config("you", foreground="#2980b9", font=("Consolas", 10, "bold"))
        self.chat_display.tag_config("vm", foreground="#27ae60", font=("Consolas", 10, "bold"))
        self.chat_display.tag_config("system", foreground="#7f8c8d", font=("Consolas", 9, "italic"))

        input_frame = tk.Frame(main_container)
        input_frame.pack(fill=tk.X, side=tk.BOTTOM, pady=(10, 0))

        tk.Label(input_frame, text="Type or paste your message:", font=("Arial", 10, "bold")).pack(anchor=tk.W,
                                                                                                   pady=(0, 5))

        text_frame = tk.Frame(input_frame)
        text_frame.pack(fill=tk.BOTH, expand=True, pady=5)

        self.message_entry = scrolledtext.ScrolledText(text_frame, height=4,
                                                       font=("Arial", 11),
                                                       wrap=tk.WORD)
        self.message_entry.pack(fill=tk.BOTH, expand=True)
        self.message_entry.bind("<Return>", self.on_enter_key)

        button_frame = tk.Frame(input_frame)
        button_frame.pack(fill=tk.X, pady=5)

        self.send_btn = tk.Button(button_frame, text="Send (Enter)", command=self.send_message,
                                  bg="#3498db", fg="white", font=("Arial", 10, "bold"),
                                  width=15, height=2, state=tk.DISABLED)
        self.send_btn.pack(side=tk.LEFT, padx=(0, 5))

        clear_btn = tk.Button(button_frame, text="Clear Chat", command=self.clear_chat,
                              bg="#95a5a6", fg="white", font=("Arial", 10),
                              width=15, height=2)
        clear_btn.pack(side=tk.LEFT)

        info_label = tk.Label(input_frame, text="Ctrl+V to paste | Enter to send",
                              font=("Arial", 9, "italic"), fg="#7f8c8d", bg="white")
        info_label.pack(pady=(5, 0))

    def on_enter_key(self, event):
        """Handle Enter key"""
        if event.state & 0x1:
            return
        else:
            self.send_message()
            return "break"

    def add_message(self, text, sender="system"):
        if not self.window.winfo_exists():
            return

        def gui_update():
            if not self.window.winfo_exists():
                return

            self.chat_display.config(state=tk.NORMAL)
            timestamp = time.strftime("%H:%M:%S")

            if sender == "you":
                self.chat_display.insert(tk.END, f"[{timestamp}] You: ", "you")
                self.chat_display.insert(tk.END, f"{text}\n")
            elif sender == "vm":
                self.chat_display.insert(tk.END, f"[{timestamp}] VM: ", "vm")
                self.chat_display.insert(tk.END, f"{text}\n")
            else:
                self.chat_display.insert(tk.END, f"[{timestamp}] {text}\n", "system")

            self.chat_display.config(state=tk.DISABLED)
            self.chat_display.see(tk.END)

        self.chat_display.after(0, gui_update)

    def clear_chat(self):
        """Clear chat"""
        self.chat_display.config(state=tk.NORMAL)
        self.chat_display.delete(1.0, tk.END)
        self.chat_display.config(state=tk.DISABLED)

    def connect(self):
        """Connect to VM"""

        def do_connect():
            try:
                self.add_message(f"Connecting to {self.vm_ip}:{self.port}...")
                self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.sock.settimeout(10)
                self.sock.connect((self.vm_ip, self.port))
                self.sock.settimeout(None)

                self.connected = True
                self.running = True

                self.status_label.config(text=f"Connected to {self.vm_ip}:{self.port}")
                self.send_btn.config(state=tk.NORMAL)
                self.message_entry.focus()

                self.add_message("Connected! Start typing...", "system")

                self.reader_thread = threading.Thread(target=self.receive_messages, daemon=True)
                self.reader_thread.start()

            except Exception as e:
                self.add_message(f"Connection failed: {e}", "system")
                self.status_label.config(text="Connection Failed", bg="#e74c3c")
                messagebox.showerror("Connection Error", f"Could not connect:\n{e}")
                self.close()

        threading.Thread(target=do_connect, daemon=True).start()

    def receive_messages(self):
        """Receive messages"""
        buffer = ""
        while self.running and self.connected:
            try:
                data = self.sock.recv(4096)
                if not data:
                    self.add_message("VM disconnected", "system")
                    self.disconnect()
                    break

                text = data.decode('utf-8', errors='ignore')
                buffer += text

                while '\n' in buffer:
                    line, buffer = buffer.split('\n', 1)
                    if line.strip():
                        self.add_message(line.strip(), "vm")

            except Exception as e:
                if self.running:
                    self.add_message(f"Error: {e}", "system")
                break

    def send_message(self):
        """Send message"""
        message = self.message_entry.get("1.0", tk.END).strip()
        if not message or not self.connected:
            return

        try:
            self.sock.sendall((message + '\n').encode('utf-8'))
            self.add_message(message, "you")
            self.message_entry.delete("1.0", tk.END)
            self.message_entry.focus()
        except Exception as e:
            self.add_message(f"Error: {e}", "system")
            self.disconnect()

    def disconnect(self):
        """Disconnect"""
        self.running = False
        self.connected = False

        if self.sock:
            try:
                self.sock.close()
            except:
                pass

        self.status_label.config(text="Disconnected", bg="#e74c3c")
        self.send_btn.config(state=tk.DISABLED)

    def close(self):
        self.running = False  # stop background thread
        self.disconnect()
        if self.window.winfo_exists():
            self.window.destroy()
        if self.on_close_callback:
            self.on_close_callback()


# ============================================
# GUI APPLICATION
# ============================================

class InstallerGUI:
    def __init__(self):
        self.window = tk.Tk()
        self.window.title("Copy-Paste Tool | by mouones (vibecoding)")

        # Calculate window size to match image aspect ratio (bottom 60% of 2256x3680)
        # Bottom 60% = 2256 x 2208
        img_width = 2256
        img_height = 2208  # Bottom 60%

        # Scale to fit screen (max 80% of screen)
        screen_width = self.window.winfo_screenwidth()
        screen_height = self.window.winfo_screenheight()

        max_width = int(screen_width * 0.8)
        max_height = int(screen_height * 0.8)

        aspect = img_width / img_height

        if max_width / aspect <= max_height:
            win_width = max_width
            win_height = int(max_width / aspect)
        else:
            win_height = max_height
            win_width = int(max_height * aspect)

        self.window.geometry(f"{win_width}x{win_height}")
        self.window.minsize(600, 400)

        self.system = platform.system()
        self.is_windows = (self.system == "Windows")

        self.vm_ip = tk.StringVar(value="192.168.100.93")
        self.port = tk.StringVar(value="4444")
        self.status_text = tk.StringVar(value="Ready")
        self.chat_window = None
        self.menu_open = False

        self.window.bind("<Configure>", self.on_resize)

        self.bg_label = None
        self.bg_photo = None
        self.create_background()

        self.create_widgets()
        self.detect_files()

    def on_resize(self, event):
        """Handle resize"""
        if event.widget == self.window and HAS_PIL:
            if hasattr(self, '_resize_after_id'):
                self.window.after_cancel(self._resize_after_id)
            self._resize_after_id = self.window.after(100, self.update_background)

    def update_background(self):
        """Update background"""
        if not HAS_PIL or not self.bg_label:
            return

        width = self.window.winfo_width()
        height = self.window.winfo_height()

        if width > 1 and height > 1:
            bg_image = create_gradient_background(width, height)
            self.bg_photo = ImageTk.PhotoImage(bg_image)
            self.bg_label.configure(image=self.bg_photo)

    def create_background(self):
        """Create background"""
        if not HAS_PIL:
            self.window.configure(bg="#2c3e50")
            return

        width = self.window.winfo_width() if self.window.winfo_width() > 1 else 800
        height = self.window.winfo_height() if self.window.winfo_height() > 1 else 600

        bg_image = create_gradient_background(width, height)
        self.bg_photo = ImageTk.PhotoImage(bg_image)

        self.bg_label = tk.Label(self.window, image=self.bg_photo)
        self.bg_label.place(x=0, y=0, relwidth=1, relheight=1)

    def create_widgets(self):
        """Create widgets"""

        # Hamburger menu button (top-left)
        self.menu_btn = tk.Button(self.window, text="☰", command=self.toggle_menu,
                                  bg="#1a1a1a", fg="white", font=("Arial", 20, "bold"),
                                  relief=tk.FLAT, cursor="hand2", width=3, height=1,
                                  borderwidth=0)
        self.menu_btn.place(x=10, y=10)

        # Status label (next to menu)
        status_label = tk.Label(self.window, text="Status:", font=("Arial", 10, "bold"),
                                fg="#ffffff", bg="#1a1a1a", padx=10, pady=5)
        status_label.place(x=70, y=15)

        self.status_display = tk.Label(self.window, textvariable=self.status_text,
                                       font=("Arial", 10), fg="#27ae60", bg="#1a1a1a",
                                       padx=5, pady=5)
        self.status_display.place(x=135, y=15)

        # Collapsible menu panel
        self.menu_frame = tk.Frame(self.window, bg="#1a1a1a", relief=tk.FLAT)
        self.menu_frame.place(x=10, y=60, width=500, height=100)
        self.menu_frame.place_forget()  # Hidden by default

        # IP and Port in same line
        form_frame = tk.Frame(self.menu_frame, bg="#1a1a1a")
        form_frame.pack(padx=15, pady=15)

        tk.Label(form_frame, text="VM IP:", font=("Arial", 11, "bold"),
                 fg="#ffffff", bg="#1a1a1a").grid(row=0, column=0, padx=(0, 10))

        ip_entry = tk.Entry(form_frame, textvariable=self.vm_ip, width=20,
                            font=("Arial", 11), bg="#2d2d2d", fg="#ffffff",
                            relief=tk.FLAT, insertbackground="#ffffff")
        ip_entry.grid(row=0, column=1, padx=5, ipady=5)

        tk.Label(form_frame, text="Port:", font=("Arial", 11, "bold"),
                 fg="#ffffff", bg="#1a1a1a").grid(row=0, column=2, padx=(20, 10))

        port_entry = tk.Entry(form_frame, textvariable=self.port, width=10,
                              font=("Arial", 11), bg="#2d2d2d", fg="#ffffff",
                              relief=tk.FLAT, insertbackground="#ffffff")
        port_entry.grid(row=0, column=3, padx=5, ipady=5)

        if not self.is_windows:
            auto_btn = tk.Button(form_frame, text="Auto", command=self.auto_detect_ip,
                                 bg="#3498db", fg="white", font=("Arial", 9),
                                 relief=tk.FLAT, cursor="hand2", padx=10)
            auto_btn.grid(row=0, column=4, padx=(10, 0))

        # Log frame (hidden by default, shown in menu)
        self.log_frame = tk.Frame(self.window, bg="#1a1a1a")
        self.log_frame.place_forget()

        tk.Label(self.log_frame, text="Log:", font=("Arial", 10, "bold"),
                 fg="#ffffff", bg="#1a1a1a").pack(anchor=tk.W, padx=10, pady=(10, 5))

        self.log_text = scrolledtext.ScrolledText(self.log_frame, height=8,
                                                  font=("Consolas", 9),
                                                  bg="#0d0d0d", fg="#b0b0b0",
                                                  wrap=tk.WORD, relief=tk.FLAT)
        self.log_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))

        # Bottom buttons bar
        button_frame = tk.Frame(self.window, bg="#1a1a1a")
        button_frame.place(relx=0.5, rely=0.95, anchor=tk.CENTER)

        button_style = {
            'font': ("Arial", 11, "bold"),
            'relief': tk.FLAT,
            'cursor': "hand2",
            'width': 16,
            'height': 2,
            'borderwidth': 0
        }

        if self.is_windows:
            self.install_btn = tk.Button(button_frame, text="Start Installation",
                                         command=self.start_windows_install,
                                         bg="#27ae60", fg="white", **button_style)
            self.install_btn.pack(side=tk.LEFT, padx=8)

            self.chat_btn = tk.Button(button_frame, text="Open Chat",
                                      command=self.open_chat,
                                      bg="#3498db", fg="white", state=tk.DISABLED, **button_style)
            self.chat_btn.pack(side=tk.LEFT, padx=8)
        else:
            self.install_btn = tk.Button(button_frame, text="Create Server",
                                         command=self.start_linux_install,
                                         bg="#27ae60", fg="white", **button_style)
            self.install_btn.pack(side=tk.LEFT, padx=8)

            self.run_btn = tk.Button(button_frame, text="Run Server",
                                     command=self.run_linux_server,
                                     bg="#3498db", fg="white", state=tk.DISABLED, **button_style)
            self.run_btn.pack(side=tk.LEFT, padx=8)

        help_btn = tk.Button(button_frame, text="Help", command=self.show_help,
                             bg="#95a5a6", fg="white", font=("Arial", 11, "bold"),
                             relief=tk.FLAT, cursor="hand2", width=8, height=2, borderwidth=0)
        help_btn.pack(side=tk.LEFT, padx=8)

    def toggle_menu(self):
        """Toggle menu visibility"""
        if self.menu_open:
            self.menu_frame.place_forget()
            self.log_frame.place_forget()

    def toggle_menu(self):
        """Toggle menu visibility"""
        if self.menu_open:
            self.menu_frame.place_forget()
            self.log_frame.place_forget()
            self.menu_open = False
        else:
            self.menu_frame.place(x=10, y=60, width=500, height=80)
            self.log_frame.place(x=10, y=150, width=500, height=250)
            self.menu_open = True

    def log(self, message, level="INFO"):
        """Add message to log"""
        self.log_text.insert(tk.END, f"[{level}] {message}\n")
        self.log_text.see(tk.END)
        self.window.update()

    def update_status(self, message, color="#27ae60"):
        """Update status label"""
        self.status_text.set(message)
        self.status_display.config(fg=color)

    def auto_detect_ip(self):
        """Auto-detect local IP"""
        ip = get_local_ip()
        self.vm_ip.set(ip)
        self.log(f"Auto-detected IP: {ip}", "SUCCESS")

    def detect_files(self):
        """Detect if files already exist"""
        if self.is_windows:
            if os.path.exists('.venv/windows_client.ps1') and os.path.exists('vm_server.py'):
                self.log("Found existing installation files", "SUCCESS")
                self.chat_btn.config(state=tk.NORMAL)
        else:
            if os.path.exists('vm_server.py'):
                self.log("Found existing vm_server.py", "SUCCESS")
                self.run_btn.config(state=tk.NORMAL)

    def open_chat(self):
        """Open live chat window"""
        if self.chat_window:
            messagebox.showinfo("Chat", "Chat window is already open!")
            return

        vm_ip = self.vm_ip.get().strip()
        port = int(self.port.get().strip())

        self.chat_window = LiveChatClient(self.window, vm_ip, port,
                                          on_close_callback=lambda: setattr(self, 'chat_window', None))

    def start_windows_install(self):
        """Windows installation process"""
        self.install_btn.config(state=tk.DISABLED)
        self.update_status("Installing...", "#f39c12")

        def install():
            try:
                vm_ip = self.vm_ip.get().strip()
                port = int(self.port.get().strip())

                self.log("Starting Windows installation...")
                self.log(f"Target VM: {vm_ip}:{port}")

                self.log("Creating vm_server.py...")
                create_vm_server()
                self.log("✓ vm_server.py created", "SUCCESS")

                self.log("Creating windows_client.ps1...")
                create_windows_client(vm_ip, port)
                self.log("✓ windows_client.ps1 created", "SUCCESS")

                self.log("\n" + "=" * 50, "WARNING")
                self.log("ACTION REQUIRED ON VM:", "WARNING")
                self.log(f"Run this command on your VM NOW:", "WARNING")
                self.log(f"    nc -l {vm_ip} {port} > vm_server.py", "WARNING")
                self.log("=" * 50 + "\n", "WARNING")

                response = messagebox.askyesno(
                    "VM Setup Required",
                    f"On your VM, run this command NOW:\n\n"
                    f"nc -l {vm_ip} {port} > vm_server.py\n\n"
                    f"Press YES after starting 'nc -l' on VM"
                )

                if not response:
                    self.log("Installation cancelled by user", "WARNING")
                    self.install_btn.config(state=tk.NORMAL)
                    self.update_status("Cancelled", "#e74c3c")
                    return

                self.log(f"Sending vm_server.py to {vm_ip}:{port}...")
                self.update_status("Sending file to VM...", "#3498db")

                success, msg = send_file_to_vm(vm_ip, port, 'vm_server.py')

                if success:
                    self.log("✓ File sent successfully!", "SUCCESS")
                    self.log("\n" + "=" * 50, "SUCCESS")
                    self.log("NEXT STEPS ON VM:", "SUCCESS")
                    self.log("1. Verify: cat vm_server.py", "SUCCESS")
                    self.log("2. Run: python vm_server.py", "SUCCESS")
                    self.log("=" * 50 + "\n", "SUCCESS")

                    self.update_status("✓ Installation Complete!", "#27ae60")
                    self.chat_btn.config(state=tk.NORMAL)

                    messagebox.showinfo(
                        "Success",
                        "Installation complete!\n\n"
                        "On your VM, run:\n"
                        "python vm_server.py\n\n"
                        "Then click 'Open Chat' button"
                    )
                else:
                    self.log(f"✗ Failed to send file: {msg}", "ERROR")
                    self.update_status("Installation Failed", "#e74c3c")
                    self.install_btn.config(state=tk.NORMAL)
                    messagebox.showerror("Error", f"Failed to send file:\n{msg}")

            except Exception as e:
                self.log(f"✗ Error: {e}", "ERROR")
                self.update_status("Error", "#e74c3c")
                self.install_btn.config(state=tk.NORMAL)
                messagebox.showerror("Error", str(e))

        threading.Thread(target=install, daemon=True).start()

    def start_linux_install(self):
        """Linux installation process"""
        self.install_btn.config(state=tk.DISABLED)
        self.update_status("Creating files...", "#3498db")

        try:
            local_ip = get_local_ip()
            self.log(f"Your VM IP: {local_ip}")

            self.log("Creating vm_server.py...")
            create_vm_server()
            self.log("✓ vm_server.py created", "SUCCESS")

            self.log("\n" + "=" * 50, "SUCCESS")
            self.log("SETUP COMPLETE!", "SUCCESS")
            self.log(f"Give this IP to Windows: {local_ip}", "SUCCESS")
            self.log("=" * 50 + "\n", "SUCCESS")

            self.update_status("✓ Server file ready", "#27ae60")
            self.run_btn.config(state=tk.NORMAL)

            messagebox.showinfo(
                "Success",
                f"vm_server.py created!\n\n"
                f"Your VM IP: {local_ip}\n\n"
                f"Give this IP to Windows host,\n"
                f"then click 'Run Server' button"
            )

        except Exception as e:
            self.log(f"✗ Error: {e}", "ERROR")
            self.update_status("Error", "#e74c3c")
            self.install_btn.config(state=tk.NORMAL)
            messagebox.showerror("Error", str(e))

    def run_linux_server(self):
        """Run Linux server"""
        if not os.path.exists('vm_server.py'):
            messagebox.showerror("Error", "vm_server.py not found!")
            return

        self.log("Starting server...")
        self.log("Server will run in terminal. Press Ctrl+C to stop.")
        self.update_status("Server running in terminal...", "#27ae60")

        try:
            subprocess.call(['python', 'vm_server.py'])
        except KeyboardInterrupt:
            self.log("Server stopped", "WARNING")
        except Exception as e:
            self.log(f"Error: {e}", "ERROR")
            messagebox.showerror("Error", str(e))

    def show_help(self):
        """Show help dialog"""
        if self.is_windows:
            help_text = """WINDOWS SETUP:

1. Enter your VM's IP address
2. Click 'Start Installation'
3. On VM, run: nc -l [IP] 4444 > vm_server.py
4. Wait for file transfer
5. On VM, run: python vm_server.py
6. Click 'Open Chat' to type directly in GUI!

FEATURES:
- Type directly in the chat window
- Real-time bidirectional communication
- Resizable interface

TROUBLESHOOTING:
- If "script cannot be loaded" error:
  Run PowerShell as Administrator
- Check firewall allows port 4444
- Verify VM is reachable with: ping [VM_IP]"""
        else:
            help_text = """LINUX/VM SETUP:

1. Click 'Create Server File'
2. Note your VM IP address
3. Give IP to Windows host
4. Click 'Run Server'
5. On Windows, run auto_installer.py
6. Windows user can type in GUI!

TROUBLESHOOTING:
- Install netcat: sudo yum install nc
- Check Python: python --version
- Open firewall: sudo firewall-cmd --add-port=4444/tcp"""

        messagebox.showinfo("Help", help_text)

    def run(self):
        """Start GUI"""
        self.log(f"Installer started on {self.system}")
        self.log("Click menu button to configure settings")
        self.window.mainloop()


# ============================================
# CONSOLE MODE (Fallback if no GUI)
# ============================================

def console_mode():
    """Console-based installer"""
    print("\n" + "=" * 60)
    print("    Real-Time Copy-Paste Tool - Console Installer")
    print("    by mouones (vibecoding)")
    print("=" * 60 + "\n")

    system = platform.system()
    print(f"Detected OS: {system}\n")

    if system == "Windows":
        print("Windows Setup\n")
        vm_ip = input("Enter VM IP [192.168.100.93]: ").strip() or "192.168.100.93"
        port = input("Enter Port [4444]: ").strip() or "4444"
        port = int(port)

        print("\nCreating files...")
        create_vm_server()
        create_windows_client(vm_ip, port)
        print("✓ Files created\n")

        print("=" * 60)
        print("On your VM, run this command NOW:")
        print(f"    nc -l {vm_ip} {port} > vm_server.py")
        print("=" * 60)
        input("\nPress Enter after starting 'nc -l' on VM...")

        print("\nSending file...")
        success, msg = send_file_to_vm(vm_ip, port, 'vm_server.py')

        if success:
            print("✓ File sent successfully!\n")
            print("On VM, run: python vm_server.py")
            print("Then run GUI again and click 'Open Chat' button")
        else:
            print(f"✗ Error: {msg}")

    elif system == "Linux":
        print("Linux/VM Setup\n")
        local_ip = get_local_ip()
        print(f"Your VM IP: {local_ip}\n")

        print("Creating vm_server.py...")
        create_vm_server()
        print("✓ vm_server.py created\n")

        print(f"Give this IP to Windows: {local_ip}")
        print("\nRun: python vm_server.py")
    else:
        print(f"Unsupported OS: {system}")


# ============================================
# MAIN ENTRY POINT
# ============================================

def main():
    """Main entry point"""
    if HAS_GUI:
        try:
            app = InstallerGUI()
            app.run()
        except Exception as e:
            print(f"GUI Error: {e}")
            print("Falling back to console mode...\n")
            console_mode()
    else:
        print("Tkinter not available. Using console mode.\n")
        console_mode()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nInstallation cancelled by user")
        sys.exit(0)
    except Exception as e:
        print(f"\nError: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)