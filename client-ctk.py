import os
import socket
from time import sleep
from icecream.icecream import ic
from cryptography.fernet import Fernet
from utils import background, tkot_menu


import customtkinter as ctk
from tkinter import messagebox, Menu


class InteractionGUI(ctk.CTkToplevel):

    def __init__(self, parent : ctk.CTk, nick:str, sock:socket.socket, theme:str, addr : list[str, int] = None, encrypted : bool = False) -> None:
        super().__init__(parent)


        self.keep_on_top = False
        self.encrypted = encrypted
        self.nick = nick
        self.sock = sock
        self.theme = theme
        self.addr = addr
        self.parent = parent

        if self.encrypted:
            try:
                with open("key.key", "rb") as key_file:
                    key = key_file.read()
                self.fernet = Fernet(key)
            except FileNotFoundError as e:
                print(e)
                #messagebox.showinfo(title="Can't initialize Fernet", message="File key.key missing")
                return
            else:
                self.decrypt = self.fernet.decrypt
                self.encrypt = self.fernet.encrypt

        mynickis = f"HEYMYNICKIS{nick}HEYMYNICKIS".encode()
        if self.encrypted:
            mynickis = self.encrypt(mynickis)
        self.sock.send(mynickis)

        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme(self.theme)

        self.geometry("500x400")

        self.frame = ctk.CTkFrame(self)
        self.frame.pack(pady=20, padx=60, fill="both", expand=True)

        self.rc_menu = Menu(self, tearoff=False)
        self.rc_menu.add_command(label="Toggle TopMost", command=lambda:background(self.toggle_kot))

        self.label = ctk.CTkLabel(self.frame, text=f"Interaction with {addr[0]}:{addr[1]}")
        self.label.pack(pady=12, padx=10)
        self.label.bind("<Button-3>", self.tkot_menu) 

        self.textbox = ctk.CTkTextbox(self.frame, width=300)
        self.textbox.configure(state="disabled")
        self.textbox.pack(pady=12, padx=10)

        self.inputbox = ctk.CTkEntry(self.frame, placeholder_text="Send a Message")
        self.inputbox.bind("<Return>", command=lambda x:background(self.send_text))
        self.inputbox.pack(pady=12, padx=10)

        self.protocol("WM_DELETE_WINDOW", self.on_exit)
        self.resizable(0,0) #Window not resizable
        self.title(f"Interacting as {self.nick}")

        recvThread = background(self.listen_for_messages)

    def tkot_menu(self, event):
        try:
            self.rc_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.rc_menu.grab_release()

    def toggle_kot(self):
        self.keep_on_top = not(self.keep_on_top)
        self.attributes("-topmost", self.keep_on_top)
        self.update()

    def on_exit(self):
        if messagebox.askyesno("Quit?", message="Are you sure you want to quit?"):
            self.sock.close()
            self.destroy()

        self.parent.focus_force()

    def send_text(self):
        text = self.inputbox.get().encode()
        txt_tmp = text
        if self.encrypted:
            text = self.encrypt(text)
        self.textbox.configure(state="normal")
        self.sock.send(text)        
        self.textbox.insert(ctk.END, f"You: {txt_tmp.decode()}\n")
        self.textbox.configure(state="disabled")
        self.inputbox.delete(0, ctk.END)


    def listen_for_messages(self):
        encr = self.encrypted
        while True:
            try:
                data = self.sock.recv(2048)
                if encr:
                    data = self.decrypt(data)
                if not data:
                    raise ConnectionResetError("Data not available")
            except Exception as e:
                ic(e)
                self.destroy()
                return
            else:
                ddata = data.decode()
                self.textbox.configure(state="normal")
                self.textbox.insert(ctk.END, f"{ddata.strip()}\n")
                self.textbox.see(ctk.END)
                self.textbox.configure(state="disabled")
        

class ConnectionGUI:

    def __init__(self, encrypted:bool = False) -> None:
        self.encrypted = encrypted
        self.connecting = False
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        theme_path = "custom_themes/red1.json" if  os.path.exists("custom_themes/red1.json") else "dark-blue"
        self.theme = theme_path

        self.keep_on_top = False
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme(self.theme)

        self.root = ctk.CTk()
        self.title = "Connect"
        self.root.title(self.title)
        self.root.geometry("500x350")

        self.frame = ctk.CTkFrame(self.root)
        self.frame.pack(pady=20, padx=60, fill="both", expand=True)

        self.rc_menu = Menu(self.root, tearoff=False)
        self.rc_menu.add_command(label="Toggle TopMost", command=lambda:background(self.toggle_kot))

        self.label = ctk.CTkLabel(self.frame , text="TCP Client")
        self.label.pack(pady=12, padx=10)
        self.label.bind("<Button-3>", command=lambda x:tkot_menu(x, self.rc_menu))

        self.nick_entry = ctk.CTkEntry(self.frame, placeholder_text="Nickname")
        self.nick_entry.pack(pady=12, padx=10)

        self.host_entry = ctk.CTkEntry(self.frame, placeholder_text="IP Address")
        self.host_entry.pack(pady=12, padx=10)

        self.port_entry = ctk.CTkEntry(self.frame, placeholder_text="Port")
        self.port_entry.bind("<Return>", command=lambda x:self.connect())
        self.port_entry.pack(pady=12, padx=10)

        self.connect_button = ctk.CTkButton(self.frame, text="Connect", command=self.connect)
        self.connect_button.pack(pady=12, padx=10)

        self.root.protocol("WM_DELETE_WINDOW", self.on_exit)
        self.root.resizable(0,0) #Window not resizable
        self.root.mainloop()

    def toggle_kot(self):
        self.keep_on_top = not(self.keep_on_top)
        self.root.attributes("-topmost", self.keep_on_top)
        self.root.update()


    def on_exit(self):
        if messagebox.askyesno("Quit?", message="Are you sure you want to quit?"):
            self.sock.close()
            self.root.destroy()

    def get_addr_from_entry(self):
        nick : str = self.nick_entry.get()
        if not nick or nick.isspace():
            messagebox.showinfo("That's not a valid nickname")
            return False
        host : str = self.host_entry.get()
        port : int= self.port_entry.get()
        return nick, host, port

    def connect(self):
        if not self.connecting:
            args_for_conn = self.get_addr_from_entry()
            if args_for_conn:
                connection_thread = background(self.connect_function, args=args_for_conn)

    def connect_function(self, nick : str, host : str, port : int) -> None:
        encr = self.encrypted
        self.connecting = 1
        self.connect_button.configure(text="Connecting...")
        self.connect_button["state"] = "disabled"
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        print(f"connect: NICK: {nick} HOST:{host}, PORT:{port}")

        if port.isdigit():
            port = int(port)
            if not(port in range(1025, 65535)):
                messagebox.showinfo(title="Bad Port Format", message="Port must be between 1025 and 65535")
                self.connect_button.configure(text="Connect", state="normal")
                self.connecting = 0
                return
        else:
            messagebox.showinfo(title="Bad Port Format", message="Port must be an integer")
            self.connect_button.configure(text="Connect", state="normal")
            self.connecting = 0
            return
        
        exceptions = []
        for i in range(5):
            try:
                self.sock.connect((host, port))

            except socket.gaierror as e:
                self.connect_button.configure(text="Connect", state="normal")
                messagebox.showinfo(title="G.A.I. Error", message="Get Address Info failed")
                self.connecting = 0
                return e
            
            except Exception as e:
                ic(e)
                exceptions.append(e)
            else:
                self.addr = host, port
                self.root.wm_title("Opening Interaction Window...")
                self.connect_button.configure(text="Connect", state="normal")
                self.connecting = 0

                self.start_inteaction_gui(self.root, nick, self.sock, self.theme, self.addr, self.encrypted)
                self.root.iconify()
                self.root.wm_title(self.title)
                break

        if len(exceptions):
            return exceptions[-1]
        else:
            return True
    
    @staticmethod
    def start_inteaction_gui(master, nick, connection, theme, addr, encrypted=False) -> None:
        interactionGui = InteractionGUI(master, nick, connection, theme, addr, encrypted=encrypted)
        interactionGui.grab_set()

if __name__ == "__main__":
    connection_gui = ConnectionGUI(encrypted=True)