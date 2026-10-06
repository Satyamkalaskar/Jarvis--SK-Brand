"""
J.A.R.V.I.S. for Windows - always-on voice assistant that controls your PC.
Runs visibly in a console window. Say "exit" or "stop listening" to quit.
Dangerous actions (shutdown, restart, closing apps, running commands) ask for confirmation.
"""
import os, sys, time, random, subprocess, webbrowser, ctypes, datetime
import speech_recognition as sr
import pyttsx3, pyautogui, psutil

WAKE_WORD = ""          # set to "jarvis" to require the wake word, "" = always react
pyautogui.FAILSAFE = True   # slam mouse into a screen corner to abort automation

engine = pyttsx3.init()
engine.setProperty("rate", 175)
rec = sr.Recognizer()
rec.pause_threshold = 0.8

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
         "I would tell you a UDP joke, but you might not get it."]


def say(text):
    print("JARVIS:", text)
    engine.say(text)
    engine.runAndWait()


def hear(timeout=None, limit=10):
    with sr.Microphone() as src:
        rec.adjust_for_ambient_noise(src, duration=0.3)
        try:
            audio = rec.listen(src, timeout=timeout, phrase_time_limit=limit)
            return rec.recognize_google(audio).lower()
        except (sr.WaitTimeoutError, sr.UnknownValueError):
            return ""
        except sr.RequestError:
            print("(speech service unreachable - check internet)")
            time.sleep(2)
            return ""


def confirm(question):
    say(question + " Say yes to confirm.")
    return "yes" in hear(timeout=6, limit=4)


def launch(target):
    try:
        os.startfile(target) if target.endswith(":") else subprocess.Popen(f'start "" "{target}"', shell=True)
        return True
    except Exception:
        return False


def handle(q):
    if any(w in q for w in ("exit", "stop listening", "shut yourself down", "goodbye")):
        say("Powering down. Goodbye, sir.")
        sys.exit(0)
    if q.startswith(("hello", "hi ", "hey")):
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
    if any(w in q for w in ("play", "pause", "resume")) and "music" in q or q in ("play", "pause"):
        pyautogui.press("playpause"); return say("Done.")
    if "next track" in q or "next song" in q:
        pyautogui.press("nexttrack"); return say("Skipping.")
    if "minimize all" in q or "show desktop" in q:
        pyautogui.hotkey("win", "d"); return say("Done.")
    if "lock" in q and "pc" in q or "lock computer" in q:
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
        return say(launch(name) and f"Trying to open {name}." or f"I could not find {name}.")
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
        if confirm("Shut down the computer?"): subprocess.run("shutdown /s /t 5")
        return
    if "restart" in q:
        if confirm("Restart the computer?"): subprocess.run("shutdown /r /t 5")
        return
    if "sleep" in q and "pc" in q:
        if confirm("Put the computer to sleep?"):
            subprocess.run("rundll32.exe powrprof.dll,SetSuspendState 0,1,0")
        return
    if q.startswith("run command "):
        cmd = q[12:]
        if confirm(f"Run the command: {cmd}?"):
            out = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
            print(out.stdout or out.stderr)
            say("Command executed. Output is in the console.")
        return
    say("I don't have that command yet, sir.")


def main():
    say("J.A.R.V.I.S. online. Listening.")
    while True:
        q = hear()
        if not q:
            continue
        print("YOU:", q)
        if WAKE_WORD:
            if WAKE_WORD not in q:
                continue
            q = q.split(WAKE_WORD, 1)[1].strip(" ,")
            if not q:
                say("Yes, sir?"); continue
        try:
            handle(q)
        except SystemExit:
            raise
        except Exception as e:
            print("error:", e)
            say("Something went wrong with that command.")


if __name__ == "__main__":
    main()
