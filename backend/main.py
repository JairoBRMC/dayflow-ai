from fastapi import FastAPI

app = FastAPI(title="Dayflow AI")

@app.get("/health")
def health_check():
    return {"status": "ok"}