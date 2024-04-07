from threading import Thread
from typing import Callable
from icecream.icecream import ic
from cryptography.fernet import Fernet

def generate_key_file():
    key = Fernet.generate_key()
    with open("key.key", "wb") as key_file:
        key_file.write(key)
        
def tkot_menu(event, menu):
    try:
        menu.tk_popup(event.x_root, event.y_root)
    finally:
        menu.grab_release()

def background(function:Callable, args=None):
    if args:
        t = Thread(target=function, args=args)
    else:
        t = Thread(target=function)
    t.start()