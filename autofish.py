import cv2
import numpy as np
import mss
import time
import threading
import tkinter as tk
from PIL import Image, ImageTk
import ctypes
import keyboard  # 引入 keyboard 模組嚟偵測 F8 同做防掛機動作

# ==================== ⚙️ Resolution Settings ====================
RESOLUTION_W = 2560
RESOLUTION_H = 1440
# ================================================================

# --- Hardware-level mouse click (Bypasses Roblox anti-cheat) ---
def left_click(x, y):
    ctypes.windll.user32.SetCursorPos(int(x), int(y))
    time.sleep(0.02)
    ctypes.windll.user32.mouse_event(0x0002, 0, 0, 0, 0)
    time.sleep(0.1)
    ctypes.windll.user32.mouse_event(0x0004, 0, 0, 0, 0)

is_fishing = False

def vision_thread(status_lbl, cam_lbl, root):
    global is_fishing
    fish_completed = 0  
    FISH_COUNT_FOR_AFK = 5  # 🛡️ 每釣 5 條魚就觸發一次防掛機跳躍
    
    with mss.MSS() as sct:
        screen_w = RESOLUTION_W
        screen_h = RESOLUTION_H
        cx, cy = screen_w // 2, screen_h // 2
        
        # 💡 修正重點：將檢測區向下移（top 改為 cy - 50），避開中間嘅角色同魚竿手柄
        search_box = {
            "top": cy - 50,
            "left": cx - 300,
            "width": 600,
            "height": 600
        }

        while True:
            if not is_fishing:
                time.sleep(0.5)
                continue
                
            status_lbl.config(text="🎣 Casting...")
            left_click(cx, cy)
            
            time.sleep(3.0) 
            
            timeout = time.time() + 60 
            caught = False
            
            base_y = None  
            lock_time = time.time()
            
            while time.time() < timeout and is_fishing:
                monitor = sct.grab(search_box)
                frame = np.array(monitor)
                hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
                
                mask1 = cv2.inRange(hsv, np.array([0, 40, 30]), np.array([15, 255, 255]))
                mask2 = cv2.inRange(hsv, np.array([160, 40, 30]), np.array([180, 255, 255]))
                red_mask = mask1 + mask2
                
                contours, _ = cv2.findContours(red_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                
                bobber_found = False
                current_by = None
                
                if contours:
                    largest_red = max(contours, key=cv2.contourArea)
                    if cv2.contourArea(largest_red) > 6: 
                        bobber_found = True
                        x, y, w, h = cv2.boundingRect(largest_red)
                        
                        current_bx = x + (w // 2)
                        current_by = y + (h // 2)
                        
                        cv2.rectangle(frame, (x, y), (x + w, y + h), (255, 0, 0), 2)
                
                time_elapsed = time.time() - lock_time
                
                if time_elapsed < 2.0:
                    status_lbl.config(text="⏳ Waiting for water to settle...")
                elif not bobber_found:
                    status_lbl.config(text="🦈 Bobber obstructed or moved, waiting...")
                else:
                    if base_y is None:
                        base_y = current_by
                    
                    sink_depth = current_by - base_y
                    
                    if sink_depth < 12:
                        status_lbl.config(text=f"🐟 Nibbling / Floating... (Depth diff: {sink_depth}px)")
                    else:
                        status_lbl.config(text=f"💦 Real bite! Sunk {sink_depth}px! Reeling in!")
                        
                        target_screen_x = search_box["left"] + current_bx
                        target_screen_y = search_box["top"] + current_by
                        left_click(target_screen_x, target_screen_y)
                        
                        caught = True
                        time.sleep(1.5) 
                        
                        fish_completed += 1
                        
                        # 🛡️ 每 5 條魚收完杆後自動執行防掛機跳躍 (Jump)
                        if fish_completed >= FISH_COUNT_FOR_AFK:
                            status_lbl.config(text="🛡️ Per 5 fish: Executing Anti-AFK Jump...")
                            keyboard.press('space')
                            time.sleep(0.2)
                            keyboard.release('space')
                            fish_completed = 0  
                            time.sleep(1.0)
                            
                        break

                img_rgb = cv2.cvtColor(frame, cv2.COLOR_BGRA2RGB)
                pil_img = Image.fromarray(img_rgb).resize((400, 400))
                tk_img = ImageTk.PhotoImage(image=pil_img)
                cam_lbl.imgtk = tk_img
                cam_lbl.configure(image=tk_img)
                
                time.sleep(0.015) 
                
            if not caught and is_fishing:
                status_lbl.config(text="⏳ Timeout (No fish bit), re-casting...")

def toggle(btn, status):
    global is_fishing
    is_fishing = not is_fishing
    if is_fishing:
        btn.config(text="🛑 Stop AFK (F8)", bg="#ff4757")
        status.config(text="Running...")
    else:
        btn.config(text="▶️ Start AFK (F8)", bg="#2ed573")
        status.config(text="Idle.")

def hotkey_listener(btn, status):
    """ 監聽 F8 鍵，隨時切換開關 """
    while True:
        keyboard.wait('f8')  # 等待按下 F8
        toggle(btn, status)
        time.sleep(0.3)      # 避免按一次觸發多次

def main():
    root = tk.Tk()
    root.title(f"Islands Reborn - Auto Fish ({RESOLUTION_W}x{RESOLUTION_H})")
    root.geometry("450x550")
    root.attributes("-topmost", True) 
    
    title = tk.Label(root, text=f"Sinking Bite Tracker ({RESOLUTION_W}x{RESOLUTION_H})", font=("Arial", 16, "bold"))
    title.pack(pady=5)
    
    cam_lbl = tk.Label(root, bg="black")
    cam_lbl.pack(pady=5)
    
    status_lbl = tk.Label(root, text="Idle. Press F8 or click Start.", font=("Arial", 11))
    status_lbl.pack(pady=5)
    
    btn = tk.Button(root, text="▶️ Start AFK (F8)", bg="#2ed573", fg="white", font=("Arial", 14, "bold"), 
                    command=lambda: toggle(btn, status_lbl))
    btn.pack(pady=5)
    
    # 啟動釣魚視覺執行緒
    threading.Thread(target=vision_thread, args=(status_lbl, cam_lbl, root), daemon=True).start()
    
    # 啟動 F8 熱鍵監聽執行緒
    threading.Thread(target=hotkey_listener, args=(btn, status_lbl), daemon=True).start()
    
    root.mainloop()

if __name__ == "__main__":
    main()
