import os
import socket
import psutil
import threading
import webview
from app import app

def kill_port(port: int):
    """Find any process using the given port and terminate it."""
    try:
        for conn in psutil.net_connections(kind='inet'):
            if conn.laddr.port == port and conn.pid:
                p = psutil.Process(conn.pid)
                print(f"Terminating process {p.pid} using port {port} ({p.name()})")
                p.terminate()
                p.wait(timeout=3)
    except Exception as e:
        print(f"Could not clean port {port}: {e}")

def is_port_in_use(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('127.0.0.1', port)) == 0

def run_flask():
    app.run(host='127.0.0.1', port=5000, debug=False)

if __name__ == '__main__':
    if is_port_in_use(5000):
        kill_port(5000)

    threading.Thread(target=run_flask, daemon=True).start()

    webview.create_window(
        title='Library Management',
        url='http://127.0.0.1:5000',
        width=900,
        height=700,
        resizable=True
    )

    webview.start()
