from fastapi import FastAPI

app = FastAPI(
    title="Acompanhamento de NP",
    description="API de acompanhamento de processos no Denatran",
    version="0.1.0"
)

@app.get("/")
def read_root():
    return {"status": "ok", "message": "API wsDenatran rodando!"}
