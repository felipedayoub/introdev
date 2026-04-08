from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

app = FastAPI()

class User(BaseModel):
    nome: str
    idade: int

users = [] # Lista contendo os usuários


@app.get("/", response_class=HTMLResponse)
async def root():
    with open("index.html") as f:
        return f.read()

@app.post("/users")
async def add_user(user: User):
    users.append(user) # adiciona o usuário na lista
    return user

@app.get("/users")
async def read_user(index: int = None):
    if index == None: # Obter todos os usuários
        return users
    if 0 <= index < len(users): # Obter o usuario users[index]
        return users[index]
    return "Índice inválido" # Como proceder com requisições inválidas?

@app.delete("/users")
async def delete_users():
    users.clear()
    return "Usuários deletados"






