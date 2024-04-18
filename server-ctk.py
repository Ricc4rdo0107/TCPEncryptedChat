import os
import sys
import socket

from icecream.icecream import ic

import customtkinter as ctk
from cryptography.fernet import Fernet
from tkinter import messagebox, Menu
from utils import (background, tkot_menu, generate_key_file,
                   InvalidToken)

class Server:
    def __init__(self, encrypted=False):

        self.encrypted = encrypted
        if self.encrypted:
            if not(os.path.exists("key.key")):
                generate_key_file()
            with open("key.key", "rb") as key_file:
                key = key_file.read()

            self.fernet = Fernet(key) if self.encrypted else False
            self.decrypt = self.fernet.decrypt
            self.encrypt = self.fernet.encrypt

        self.timeouts = 0
        self.listening = False

        self.connected_clients : dict[str,socket.socket] = {}

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        theme_path = "custom_themes/red1.json" if os.path.exists("custom_themes/red1.json") else "dark-blue"
        self.theme = theme_path

        self.keep_on_top = False
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme(self.theme)

        self.root = ctk.CTk()
        self.menu = Menu(self.root)

        self.toggle_kot_menu = Menu(self.root, tearoff=False)
        self.toggle_kot_menu.add_command(label="Toggle TopMost", command=lambda:background(self.toggle_kot))

        self.sub_kick_menu = Menu(self.menu, tearoff=False)
        self.menu.add_cascade(label="Kick", menu=self.sub_kick_menu)

        self.frame = ctk.CTkFrame(self.root)
        self.frame.pack(pady=20, padx=30, fill="both")

        self.label = ctk.CTkLabel(self.frame, text="Chat Server")
        self.label.pack()
        self.label.bind("<Button-3>", command=lambda x: tkot_menu(x, self.toggle_kot_menu))

        self.textbox = ctk.CTkTextbox(self.frame, width=400)
        self.textbox.pack()

        self.broadcast_message = ctk.CTkEntry(self.frame, width=400, placeholder_text="Broadcast Message")
        self.broadcast_message.bind("<Return>", command=lambda x:self.broadcast(self.broadcast_message.get(), True))
        self.broadcast_message.pack(pady=6, padx=7)

        self.quit_button = ctk.CTkButton(self.root, text="QUIT", command=self.on_exit)
        self.quit_button.pack(pady=12, padx=15, side="left")

        self.start_button = ctk.CTkButton(self.root, text="START", command=self.startserverThr)
        self.start_button.pack(pady=12, padx=15, side="left")

        self.stop_button = ctk.CTkButton(self.root, text="STOP", command=self.close_server)
        self.stop_button.pack(pady=12, padx=15, side="left")

        self.root.configure(menu=self.menu)
        self.root.protocol("WM_DELETE_WINDOW", self.on_exit)
        self.root.geometry("500x400")
        self.root.resizable(0,0)           #Window not resizable 0=False
        self.root.title("Chat Server")
        self.root.mainloop()               #Starting window loop


    def toggle_kot(self):                  #Toggle keep on top
        self.keep_on_top = not(self.keep_on_top)
        self.root.attributes("-topmost", self.keep_on_top)
        self.root.update()


    def update_kick_menu(self):
        self.sub_kick_menu.delete(0, "end")
        for name, sock in self.connected_clients.items():
            self.sub_kick_menu.add_command(label=name, command=sock.close)


    def close_server(self):
        for client in self.connected_clients.values():
            client.close()
        try:
            self.sock.shutdown(2)
            self.sock.close()
        except:
            self.sock.close()
        finally:
            self.cleartextbox()
            self.tprint("Server closed")


    def handle_client(self, sock:socket.socket, raddr:tuple):
        encr = self.encrypted
        try:
            sock.settimeout(2)
            name = sock.recv(1024).decode().strip()
            if encr:
                try:
                    name = self.decrypt(name).decode()
                except InvalidToken:
                    ic(f"Invalid token by {raddr[0]}{raddr[1]}")
                    self.tprint(f"{raddr[0]}:{raddr[1]} tried to use an invalid cryptography token")
                    sock.close()
            if name.startswith("HEYMYNICKIS") and name.endswith("HEYMYNICKIS"):
                name = name.replace("HEYMYNICKIS", "")
                if name in self.connected_clients.keys():
                    sock.send(self.encrypt(b"Name alredy in use"))
                    sock.close()
                    return
                self.connected_clients.update({name:sock})
            else:
                sock.close()
                return

        except socket.timeout:
            self.timeouts += 1
            sock.close()
            return

        except Exception as e:
            sock.close()
            return
        
        self.update_kick_menu()
        self.broadcast(f"{name} joined the room", exclude=sock)
        self.tprint(f"{name} joined the room ({raddr})")
        sock.settimeout(None)

        while True:
            try:
                data = sock.recv(2048)
                if encr:
                    try:
                        data = self.decrypt(data)
                    except InvalidToken:
                        ic(f"Invalid token by {raddr[0]}:{raddr[1]}")
                        self.tprint(f"{raddr[0]}:{raddr[1]} tried to use an invalid cryptography token")
                        sock.close()
                        break
                ddata = data.decode()

                if not data:
                    raise ConnectionError("No data error")
                
                if ddata and not(ddata.isspace()):
                    self.tprint(f"{name}: {ddata}")
                    self.broadcast(f"{name}: {ddata}", exclude=sock)

            except ConnectionAbortedError as e:
                ic(e)
                self.broadcast(f"{name} has been kicked", host=True)
                break

            except Exception as e:
                ic(e)
                self.tprint(f"Connection lost with {name} {raddr[0]}:{raddr[1]}")
                self.broadcast(f"Connection lost with {name}", exclude=sock)
                break
        try:
            del self.connected_clients[name]
        finally:
            self.update_kick_menu()
        return


    def on_exit(self):
        if messagebox.askyesno(title="Quit?", message="Do you really want to quit?"):
            self.close_server()
            self.root.destroy()
            sys.exit(0)


    def cleartextbox(self):
        self.textbox.configure(state="normal")
        self.textbox.delete("0.0",ctk.END)
        self.textbox.configure(state="disabled")


    def startserverThr(self):
        if not self.listening:
            new = background(self.start_server)


    def broadcast(self, text, host=False, exclude=None):
        encr = self.encrypted
        text = f"{'Host: ' if host else ''}{text}".encode()
        if host:
            self.tprint(f"You: {text.decode()}")
        if encr:
            text = self.encrypt(text)
        
        for client in self.connected_clients.values():
            if client != exclude:
                try:
                    client.send(text)
                except Exception as e:
                    ic(e)
                    client.close()
                finally:
                    pass
        self.broadcast_message.delete(0, ctk.END)


    def start_server(self, host="127.0.0.1", port=4444):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.bind((host, port))
        self.sock.listen()
        self.tprint("Listening...")
        self.listening = True
        
        while True:
            if not self.timeouts % 10 and self.timeouts > 0:
                messagebox.showwarning(title="Timeouts alert", message=f"{self.timeouts} timeouts")
            try:
                conn, raddr = self.sock.accept()
            except Exception as e:
                self.listening = False
                background(self.tprint, args=("Server is now closed",))
                break
            new_conn = background(self.handle_client, (conn, raddr))
            background(self.update_kick_menu)


    def tprint(self, text : str):
        self.textbox.configure(state="normal")
        self.textbox.insert(ctk.END, f"{text.strip()}\n")
        self.textbox.see(ctk.END)
        self.textbox.configure(state="disabled")
        return

if __name__ == "__main__":
    Server(encrypted=True)