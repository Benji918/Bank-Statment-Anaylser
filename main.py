from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from api.routes import router
import uvicorn


app = FastAPI()
app.include_router(router)

app.mount("/static", StaticFiles(directory="static"), name="static")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/", tags=['Home'])
async def root():
    return {"message": "Hello World"}






if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=2000, reload=True)