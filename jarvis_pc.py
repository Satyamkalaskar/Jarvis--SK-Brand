"""
J.A.R.V.I.S. for Windows - HUD window, always-on mic, spoken replies, PC control.
Dangerous actions (shutdown, restart, close apps, run command) show a confirmation dialog.
"""
import os, sys, time, random, subprocess, webbrowser, ctypes, datetime, threading, math
import tkinter as tk
from tkinter import messagebox
import speech_recognition as sr
import pyautogui, psutil

NOWIN = 0x08000000                     # hide console windows of child processes
pyautogui.FAILSAFE = True              # slam mouse into a screen corner to abort automation

BG, CY, DIM, TXT, WARN = "#030b14", "#38d6ff", "#12a8d8", "#cdefff", "#ffb347"

APPS = {
    "notepad": "notepad", "calculator": "calc", "paint": "mspaint", "cmd": "cmd",
    "command prompt": "cmd", "task manager": "taskmgr", "explorer": "explorer",
    "file explorer": "explorer", "chrome": "chrome", "edge": "msedge", "firefox": "firefox",
    "word": "winword", "excel": "excel", "powerpoint": "powerpnt", "spotify": "spotify",
    "settings": "ms-settings:", "control panel": "control",
}
SITES = {"youtube": "youtube.com", "google": "google.com", "gmail": "mail.google.com",
         "github": "github.com", "maps": "maps.google.com", "whatsapp": "web.whatsapp.com"}
JOKES = ["Why do programmers prefer dark mode? Because light attracts bugs.",
         "I would tell you a UDP joke, but you might not get it.",
         "There are 10 kinds of people: those who understand binary and those who don't."]

state = "ONLINE"
voice_on = True
wake_on = False
mic_on = threading.Event()
speaking = threading.Event()
last_spoke_end = 0.0
rec = sr.Recognizer()
rec.pause_threshold = 0.8

root = tk.Tk()
root.title("J.A.R.V.I.S.")
root.configure(bg=BG)
root.geometry("940x540")
root.minsize(860, 500)


# ---------------------------------------------------------------- UI helpers
def ui(fn):
    root.after(0, fn)


def log_add(who, text):
    def _add():
        tag = {"JARVIS": "j", "YOU": "u"}.get(who, "s")
        log.config(state="normal")
        log.insert("end", f"{who}: ", ("b" + tag,))
        log.insert("end", text + "\n\n", (tag,))
        log.config(state="disabled")
        log.see("end")
    ui(_add)


def set_state(s):
    global state
    state = s
    ui(lambda: state_lbl.config(text=s))


# ---------------------------------------------------------------- speech out
def say(text):
    """Speak with Windows' built-in voice (System.Speech) - works reliably inside an .exe."""
    global last_spoke_end
    log_add("JARVIS", text)
    if not voice_on:
        return
    speaking.set()
    set_state("SPEAKING")
    ps = ("Add-Type -AssemblyName System.Speech;"
          "$s=New-Object System.Speech.Synthesis.SpeechSynthesizer;"
          "try{$s.SelectVoiceByHints('Male')}catch{};"
          "$s.Speak($env:JARVIS_TEXT)")
    try:
        subprocess.run(["powershell", "-NoProfile", "-WindowStyle", "Hidden", "-Command", ps],
                       env={**os.environ, "JARVIS_TEXT": text}, creationflags=NOWIN, timeout=60)
    except Exception as e:
        log_add("SYSTEM", f"Voice error: {e}")
    speaking.clear()
    last_spoke_end = time.time()
    set_state("LISTENING" if mic_on.is_set() else "ONLINE")


def confirm(question):
    say(question)
    res, ev = {}, threading.Event()

    def ask():
        res["v"] = messagebox.askyesno("JARVIS - confirm", question)
        ev.set()
    ui(ask)
    ev.wait()
    return res["v"]


def launch(target):
    try:
        if target.endswith(":"):
            os.startfile(target)
        else:
            subprocess.Popen(f'start "" "{target}"', shell=True, creationflags=NOWIN)
        return True
    except Exception:
        return False


# ---------------------------------------------------------------- commands
def handle(q):
    if any(w in q for w in ("exit", "stop listening", "shut yourself down", "goodbye")):
        say("Powering down. Goodbye, sir.")
        time.sleep(0.5)
        os._exit(0)
    if q.startswith(("hello", "hi ", "hey")) or q in ("hi", "jarvis"):
        return say("At your service, sir.")
    if "time" in q:
        return say(datetime.datetime.now().strftime("It is %I:%M %p."))
    if "date" in q or "today" in q:
        return say(datetime.datetime.now().strftime("Today is %A, %d %B %Y."))
    if "joke" in q:
        return say(random.choice(JOKES))
    if "status" in q or "system" in q:
        b = psutil.sensors_battery()
        bat = f", battery {int(b.percent)} percent" if b else ""
        return say(f"CPU {psutil.cpu_percent(1)} percent, memory {psutil.virtual_memory().percent} percent{bat}.")
    if "screenshot" in q:
        path = os.path.join(os.path.expanduser("~"), "Pictures", f"jarvis_{int(time.time())}.png")
        pyautogui.screenshot(path)
        return say("Screenshot saved to your Pictures folder.")
    if "volume up" in q:
        pyautogui.press("volumeup", presses=5); return say("Volume increased.")
    if "volume down" in q:
        pyautogui.press("volumedown", presses=5); return say("Volume decreased.")
    if "mute" in q:
        pyautogui.press("volumemute"); return say("Done.")
    if (any(w in q for w in ("play", "pause", "resume")) and "music" in q) or q in ("play", "pause"):
        pyautogui.press("playpause"); return say("Done.")
    if "next track" in q or "next song" in q:
        pyautogui.press("nexttrack"); return say("Skipping.")
    if "minimize all" in q or "show desktop" in q:
        pyautogui.hotkey("win", "d"); return say("Done.")
    if ("lock" in q and "pc" in q) or "lock computer" in q:
        say("Locking."); return ctypes.windll.user32.LockWorkStation()
    if q.startswith("type "):
        pyautogui.write(q[5:], interval=0.03); return
    if q.startswith("press "):
        pyautogui.press(q[6:].strip()); return say("Done.")
    if q.startswith("search for ") or q.startswith("google "):
        term = q.replace("search for ", "").replace("google ", "")
        webbrowser.open("https://www.google.com/search?q=" + term.replace(" ", "+"))
        return say(f"Searching for {term}.")
    if q.startswith(("open ", "launch ", "start ")):
        name = q.split(" ", 1)[1].strip()
        if name in SITES:
            webbrowser.open("https://" + SITES[name]); return say(f"Opening {name}.")
        if name in APPS and launch(APPS[name]):
            return say(f"Opening {name}.")
        if "." in name:
            webbrowser.open("https://" + name.replace(" dot ", ".").replace(" ", "")); return say("Opening.")
        return say(f"Trying to open {name}." if launch(name) else f"I could not find {name}.")
    if q.startswith("close "):
        name = q[6:].strip()
        exe = APPS.get(name, name).lower().replace(".exe", "")
        hits = [p for p in psutil.process_iter(["name"]) if exe in (p.info["name"] or "").lower()]
        if not hits:
            return say(f"I don't see {name} running.")
        if confirm(f"Close {len(hits)} {name} process{'es' if len(hits) > 1 else ''}?"):
            for p in hits:
                try: p.terminate()
                except Exception: pass
            say("Closed.")
        return
    if "shutdown" in q or "shut down" in q:
        if confirm("Shut down the computer?"): subprocess.run("shutdown /s /t 5", creationflags=NOWIN)
        return
    if "restart" in q:
        if confirm("Restart the computer?"): subprocess.run("shutdown /r /t 5", creationflags=NOWIN)
        return
    if "sleep" in q and "pc" in q:
        if confirm("Put the computer to sleep?"):
            subprocess.run("rundll32.exe powrprof.dll,SetSuspendState 0,1,0", creationflags=NOWIN)
        return
    if q.startswith("run command "):
        cmd = q[12:]
        if confirm(f"Run the command: {cmd}?"):
            out = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30, creationflags=NOWIN)
            log_add("SYSTEM", (out.stdout or out.stderr or "(no output)").strip()[:800])
            say("Command executed.")
        return
    if "help" in q or "what can you do" in q:
        return say("I can open apps and sites, search the web, control volume and media, type, "
                   "take screenshots, lock the PC, report status, and shut down or restart with your confirmation.")
    say("I don't have that command yet, sir.")


def process(q, typed=False):
    log_add("YOU", q)
    if wake_on and not typed:
        if "jarvis" not in q:
            return
        q = q.split("jarvis", 1)[1].strip(" ,")
        if not q:
            return say("Yes, sir?")
    try:
        handle(q.lower())
    except Exception as e:
        log_add("SYSTEM", f"error: {e}")
        say("Something went wrong with that command.")


# ---------------------------------------------------------------- always-on mic loop
def listener():
    try:
        with sr.Microphone() as src:
            rec.adjust_for_ambient_noise(src, duration=0.6)
            log_add("SYSTEM", "Microphone ready.")
            while True:
                if not mic_on.is_set() or speaking.is_set():
                    time.sleep(0.2)
                    continue
                set_state("LISTENING")
                t0 = time.time()
                try:
                    audio = rec.listen(src, timeout=3, phrase_time_limit=10)
                except sr.WaitTimeoutError:
                    continue
                if speaking.is_set() or last_spoke_end > t0:
                    continue                      # ignore Jarvis hearing himself
                try:
                    q = rec.recognize_google(audio).lower()
                except sr.UnknownValueError:
                    continue
                except sr.RequestError:
                    log_add("SYSTEM", "Speech service unreachable. Check your internet.")
                    time.sleep(3)
                    continue
                process(q)
    except Exception as e:
        log_add("SYSTEM", f"Microphone error: {e}")
        set_state("MIC ERROR")


# ---------------------------------------------------------------- layout
tk.Label(root, text="J . A . R . V . I . S .", fg=CY, bg=BG, font=("Segoe UI", 18, "bold")).grid(
    row=0, column=0, sticky="w", padx=18, pady=(12, 0))
clock = tk.Label(root, fg=DIM, bg=BG, font=("Consolas", 11))
clock.grid(row=0, column=1, sticky="e", padx=18, pady=(12, 0))

left = tk.Frame(root, bg=BG)
left.grid(row=1, column=0, sticky="nsew", padx=12, pady=8)
right = tk.Frame(root, bg=BG)
right.grid(row=1, column=1, sticky="nsew", padx=12, pady=8)
root.grid_columnconfigure(0, weight=1)
root.grid_columnconfigure(1, weight=1)
root.grid_rowconfigure(1, weight=1)

W, H = 400, 330
canvas = tk.Canvas(left, width=W, height=H, bg=BG, highlightthickness=1, highlightbackground=DIM)
canvas.pack()
state_lbl = tk.Label(left, text="ONLINE", fg=CY, bg=BG, font=("Segoe UI", 12, "bold"))
state_lbl.pack(pady=(6, 4))


def btn(parent, text, cmd):
    b = tk.Button(parent, text=text, command=cmd, bg=BG, fg=CY, activebackground=DIM, activeforeground=BG,
                  relief="solid", bd=1, font=("Segoe UI", 9, "bold"), padx=8, pady=3, cursor="hand2")
    b.pack(side="left", padx=4)
    return b


bar = tk.Frame(left, bg=BG)
bar.pack()


def toggle_mic():
    if mic_on.is_set():
        mic_on.clear(); mic_b.config(text="MIC: OFF"); set_state("ONLINE")
    else:
        mic_on.set(); mic_b.config(text="MIC: ALWAYS ON")


def toggle_voice():
    global voice_on
    voice_on = not voice_on
    voice_b.config(text="VOICE: ON" if voice_on else "VOICE: OFF")


def toggle_wake():
    global wake_on
    wake_on = not wake_on
    wake_b.config(text="WAKE WORD: ON" if wake_on else "WAKE WORD: OFF")


mic_b = btn(bar, "MIC: ALWAYS ON", toggle_mic)
voice_b = btn(bar, "VOICE: ON", toggle_voice)
wake_b = btn(bar, "WAKE WORD: OFF", toggle_wake)

log = tk.Text(right, bg="#06182a", fg=TXT, insertbackground=CY, relief="flat", wrap="word",
              font=("Segoe UI", 10), state="disabled", height=18, padx=8, pady=8)
log.pack(fill="both", expand=True)
for t, c in (("j", CY), ("u", TXT), ("s", WARN)):
    log.tag_config(t, foreground=c)
    log.tag_config("b" + t, foreground=c, font=("Segoe UI", 9, "bold"))

entry_row = tk.Frame(right, bg=BG)
entry_row.pack(fill="x", pady=(8, 0))
entry = tk.Entry(entry_row, bg="#06182a", fg=TXT, insertbackground=CY, relief="solid", bd=1,
                 font=("Segoe UI", 11))
entry.pack(side="left", fill="x", expand=True, ipady=5)


def send(_=None):
    t = entry.get().strip()
    entry.delete(0, "end")
    if t:
        threading.Thread(target=process, args=(t, True), daemon=True).start()


entry.bind("<Return>", send)
tk.Button(entry_row, text="SEND", command=send, bg=BG, fg=CY, relief="solid", bd=1,
          font=("Segoe UI", 9, "bold"), padx=10).pack(side="left", padx=(6, 0))


# ---------------------------------------------------------------- arc reactor animation
angle = 0.0


def animate():
    global angle
    spd = {"LISTENING": 2.2, "SPEAKING": 4.0}.get(state, 1.2)
    angle = (angle + spd) % 360
    t = time.time()
    canvas.delete("all")
    cx, cy = W / 2, H / 2
    pulse = math.sin(t * (9 if state == "SPEAKING" else 3)) * (6 if state == "SPEAKING" else 3)
    for r, a0, ext, col, w, dash in (
            (140, angle, 100, CY, 3, None), (140, angle + 180, 100, CY, 3, None),
            (112, -angle * 0.7, 300, DIM, 2, (6, 6)),
            (84, angle * 1.6, 90, CY, 4, None), (84, angle * 1.6 + 180, 90, CY, 4, None)):
        canvas.create_arc(cx - r, cy - r, cx + r, cy + r, start=a0, extent=ext, style="arc",
                          outline=col, width=w, dash=dash)
    for i, col in enumerate(("#0a3a52", "#0f6a8c", "#1aa6d1", CY, "#e8fbff")):
        r = 46 + pulse - i * 8
        if r > 0:
            canvas.create_oval(cx - r, cy - r, cx + r, cy + r, fill=col, outline="")
    clock.config(text=datetime.datetime.now().strftime("%H:%M:%S  |  %d %b %Y"))
    root.after(33, animate)


animate()
root.protocol("WM_DELETE_WINDOW", lambda: os._exit(0))

mic_on.set()
threading.Thread(target=listener, daemon=True).start()
threading.Thread(target=lambda: say("J.A.R.V.I.S. online. I am listening, sir."), daemon=True).start()
root.mainloop()
