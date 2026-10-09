"""Todo Overlay - Floating todo list in corner"""
import tkinter as tk
import threading
from jarvis_app.tools import create_default_registry

_overlay = None
_overlay_lock = threading.Lock()

def show_todo_overlay(root):
    global _overlay
    with _overlay_lock:
        if _overlay and _overlay.winfo_exists():
            _overlay.lift()
            return
        
        _overlay = TodoOverlay(root)
        _overlay.show()

def hide_todo_overlay():
    global _overlay
    with _overlay_lock:
        if _overlay and _overlay.winfo_exists():
            _overlay.destroy()
            _overlay = None

def toggle_todo_overlay(root):
    global _overlay
    with _overlay_lock:
        if _overlay and _overlay.winfo_exists():
            _overlay.destroy()
            _overlay = None
        else:
            show_todo_overlay(root)

class TodoOverlay:
    def __init__(self, root):
        self.root = root
        self.reg = create_default_registry()
        self.colors = {
            "bg": "#0a0a1a", "fg": "#e0e0e0",
            "accent": "#00ccff", "accent2": "#1a1a3e",
            "done": "#44aa44", "pending": "#ffaa00",
        }
        self._build_ui()
        self._refresh_loop()
    
    def _build_ui(self):
        self.win = tk.Toplevel(self.root)
        self.win.title("JARVIS Tasks")
        self.win.geometry("320x400")
        self.win.configure(bg=self.colors["bg"])
        self.win.attributes("-topmost", True)
        self.win.overrideredirect(True)
        try:
            self.win.attributes("-alpha", 0.95)
        except:
            pass
        
        # Position top-right
        self.win.update_idletasks()
        sw = self.root.winfo_screenwidth()
        x = sw - 340
        y = 50
        self.win.geometry(f"+{x}+{y}")
        
        # Drag handle
        handle = tk.Frame(self.win, bg=self.colors["accent2"], height=30, cursor="fleur")
        handle.pack(fill=tk.X)
        handle.bind("<Button-1>", self._start_drag)
        handle.bind("<B1-Motion>", self._do_drag)
        
        title = tk.Label(handle, text="📋 TASKS", font=("Segoe UI", 10, "bold"),
                        fg=self.colors["accent"], bg=self.colors["accent2"])
        title.pack(side=tk.LEFT, padx=10, pady=5)
        
        close_btn = tk.Label(handle, text="✕", font=("Segoe UI", 10),
                            fg=self.colors["fg"], bg=self.colors["accent2"], cursor="hand2")
        close_btn.pack(side=tk.RIGHT, padx=10)
        close_btn.bind("<Button-1>", lambda e: self.win.destroy())
        
        # Task list
        list_frame = tk.Frame(self.win, bg=self.colors["bg"])
        list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        self.canvas = tk.Canvas(list_frame, bg=self.colors["bg"], highlightthickness=0)
        scrollbar = tk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.canvas.yview)
        self.scroll_frame = tk.Frame(self.canvas, bg=self.colors["bg"])
        
        self.scroll_frame.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.create_window((0, 0), window=self.scroll_frame, anchor="nw", width=280)
        self.canvas.configure(yscrollcommand=scrollbar.set)
        
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Add task entry
        entry_frame = tk.Frame(self.win, bg=self.colors["accent2"], height=40)
        entry_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
        entry_frame.pack_propagate(False)
        
        self.task_entry = tk.Entry(entry_frame, font=("Segoe UI", 10),
                                  bg="#1a1a2e", fg=self.colors["fg"],
                                  insertbackground=self.colors["accent"], bd=0)
        self.task_entry.pack(fill=tk.X, side=tk.LEFT, expand=True, padx=10, pady=8)
        self.task_entry.bind("<Return>", self._add_task)
        
        add_btn = tk.Label(entry_frame, text="+", font=("Segoe UI", 14),
                          fg=self.colors["accent"], bg="#1a1a2e", cursor="hand2", padx=10)
        add_btn.pack(side=tk.RIGHT, pady=5)
        add_btn.bind("<Button-1>", lambda e: self._add_task())
    
    def _start_drag(self, event):
        self._drag_x = event.x
        self._drag_y = event.y
    
    def _do_drag(self, event):
        x = self.win.winfo_x() + event.x - self._drag_x
        y = self.win.winfo_y() + event.y - self._drag_y
        self.win.geometry(f"+{x}+{y}")
    
    def _add_task(self, event=None):
        task = self.task_entry.get().strip()
        if not task:
            return
        result = self.reg.get("todo").execute({"action": "add", "task": task})
        if result.get("success"):
            self.task_entry.delete(0, tk.END)
            self._refresh_tasks()
    
    def _refresh_tasks(self):
        for widget in self.scroll_frame.winfo_children():
            widget.destroy()
        
        result = self.reg.get("todo").execute({"action": "list", "filter": "all"})
        if not result.get("success"):
            return
        
        tasks = result.get("result", "").split("\n")
        for task_line in tasks:
            if not task_line.strip():
                continue
            
            done = task_line.startswith("✓")
            task_text = task_line[2:].strip()
            task_id = ""
            if " (id: " in task_text:
                task_text, id_part = task_text.rsplit(" (id: ", 1)
                task_id = id_part.rstrip(")")
            
            row = tk.Frame(self.scroll_frame, bg=self.colors["bg"])
            row.pack(fill=tk.X, pady=2)
            
            checkbox = tk.Label(row, text="✓" if done else "☐",
                               font=("Segoe UI", 12),
                               fg=self.colors["done"] if done else self.colors["pending"],
                               bg=self.colors["bg"], cursor="hand2")
            checkbox.pack(side=tk.LEFT, padx=5)
            checkbox.bind("<Button-1>", lambda e, tid=task_id: self._toggle_done(tid))
            
            label = tk.Label(row, text=task_text, font=("Segoe UI", 9),
                            fg=self.colors["fg"], bg=self.colors["bg"],
                            anchor="w", wraplength=220, justify="left")
            label.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
            
            del_btn = tk.Label(row, text="✕", font=("Segoe UI", 8),
                              fg="#ff4444", bg=self.colors["bg"], cursor="hand2")
            del_btn.pack(side=tk.RIGHT, padx=5)
            del_btn.bind("<Button-1>", lambda e, tid=task_id: self._delete_task(tid))
    
    def _toggle_done(self, task_id):
        if not task_id:
            return
        self.reg.get("todo").execute({"action": "done", "id": task_id})
        self._refresh_tasks()
    
    def _delete_task(self, task_id):
        if not task_id:
            return
        self.reg.get("todo").execute({"action": "remove", "id": task_id})
        self._refresh_tasks()
    
    def _refresh_loop(self):
        self._refresh_tasks()
        self.win.after(5000, self._refresh_loop)
    
    def show(self):
        self.win.deiconify()
        self._refresh_tasks()
    
    def destroy(self):
        self.win.destroy()