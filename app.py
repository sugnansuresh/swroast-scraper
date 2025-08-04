import threading
from fastapi import FastAPI
from sw_scraper import main_loop
import time
app = FastAPI()

@app.get("/")
def root():
    return {"status": "runnning"}

# run scraper in a background thread
def start_scraper():
    time.sleep(1)
    main_loop()

threading.Thread(target=start_scraper, daemon=True).start()