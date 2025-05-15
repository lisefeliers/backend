from copy import deepcopy
import time
from uuid import uuid4
from fastapi import Cookie, FastAPI, Query
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

"""
Consignes :
- Notion de carte : qui aura un ensemble de keys qu'elle renverra à l'utilisateur
- user_id
- Tableau : carte avec les pixels rgb
- timeout : 10ns
"""

app = FastAPI()

app.add_middleware(CORSMiddleware,
                   allow_origins=["*", "http://localhost:8000"],
                   allow_credentials=True)

# Classe pour les utilisateurs
class UserInfos:
    last_edited_time_nanos: int
    last_seen_map: list[list[tuple[int, int, int]]]

    def __init__(self,carte):
        self.last_seen_map = deepcopy(carte)
        self.last_edited_time_nanos = round(time.time() * 1e9)

# Classe pour les cartes
class Carte:
    keys: set[str]
    users: dict[str, UserInfos]
    nx: int
    ny: int
    timeout_nanos: int
    data: list[list[tuple[int, int, int]]]

    def __init__(self, nx: int, ny: int, timeout_nanos: int = 10000000000):
        self.nx = nx
        self.ny = ny
        self.keys = set()
        self.users = {}
        self.data = [
            [(0, 0, 0) for _ in range(ny)] for _ in range(nx)
        ]
        self.timeout_nanos = timeout_nanos

    def create_new_key(self):
        key = str(uuid4())
        self.keys.add(key)
        return key
    
    def is_valid_key(self, key: str):
        return key in self.keys
    
    def create_new_user_id(self):
        user_id = str(uuid4())
        self.users[user_id] = UserInfos(self.data)
        return user_id
    
    def is_valid_user_id(self, user_id: str):  
        return user_id in self.users


cartes : dict[str, Carte] = {
    "000": Carte(nx=10, ny=10),
}

@app.get("/")
async def root():
    return {"Message": "My Pixels War project"}

@app.get("/api/v1/{nom_carte}/preinit")
async def preinit(nom_carte: str):
    carte = cartes[nom_carte]
    if not carte in cartes:
        return {"error": "Carte not found"}
    
    key = cartes[carte].create_new_key()
    res = JSONResponse({"key": key})
    res.set_cookie("key", key, secure=True, samesite="None", max_age=3600)
    return res


@app.get("/api/v1/{nom_carte}/init")
async def init(nom_carte: str, 
               query_key: str = Query(alias="key"),
               cookie_key: str = Cookie(alias="key")):
    carte = cartes[nom_carte]

    if not carte in cartes:
        return {"error": "Carte not found"}
    
    if query_key != cookie_key:
        return {"error": "Key mismatch"}
    
    if not carte.is_valid_key(cookie_key):
        return {"error": "Invalid key"}
    
    user_id = carte.create_new_user_id()

    res = JSONResponse({"id": user_id, 
            "nx": carte.nx, 
            "ny": carte.ny, 
            "timeout" : carte.timeout_nanos, 
            "data": carte.data})
    res.set_cookie("id", user_id, secure=True, samesite="None", max_age=3600)
    return res

@app.get("/api/v1/{nom_carte}/deltas")
async def deltas(nom_carte: str, 
            query_user_id: str = Query(alias="id"),
            cookie_key: str = Cookie(alias="key"),
            cookie_user_id: str = Cookie(alias="id")):
    carte = cartes[nom_carte]

    if not carte in cartes:
        return {"error": "Carte not found"}
    
    if query_user_id != cookie_user_id:
        return {"error": "User ID mismatch"}
    
    if not carte.is_valid_key(cookie_key):
        return {"error": "Invalid key"}
    
    if not carte.is_valid_user_id(cookie_user_id):
        return {"error": "Invalid user ID"}
    
    user_info = carte.users[query_user_id]
    user_carte = user_info.last_seen_map

    deltas: list[tuple[int, int, int, int, int]] = []
    for y in range(carte.ny):
        for x in range(carte.nx):
            if carte.data[x][y] != user_carte[x][y]:
                deltas.append((y, x, *carte.data[x][y]))

    return {
        "id": query_user_id,
        "nx": carte.nx, 
        "ny": carte.ny,
        "timeout": carte.timeout_nanos,
        "deltas": deltas
    }

"""
Autre possibilité :
stocker les modifs dans un tableau et pour chaque utilisateur, l'indice du dernier qu'il a reçu
"""

@app.get("/api/v1/{nom_carte}/set/{user_id}/y/x/r/g/b")
async def set_pixel(nom_carte: str, 
                    x: int, 
                    y: int, 
                    r: int, 
                    g: int, 
                    b: int,
                    query_user_id: str = Query(alias="id"), 
                    cookie_key: str = Cookie(alias="key"),
                    cookie_user_id: str = Cookie(alias="id")):
    carte = cartes[nom_carte]

    if not carte in cartes:
        return {"error": "Carte not found"}
    
    if query_user_id != cookie_user_id:
        return {"error": "User ID mismatch"}
    
    if not carte.is_valid_key(cookie_key):
        return {"error": "Invalid key"}
    
    if not carte.is_valid_user_id(query_user_id):
        return {"error": "Invalid user ID"}
    
    last_edited_time = carte.users[query_user_id].last_edited_time_nanos
    current_time = round(time.time() * 1e9)
    if current_time - last_edited_time > carte.timeout_nanos:
        carte.data[x][y] = (r, g, b)
        carte.users[query_user_id].last_seen_map = deepcopy(carte.data)
        carte.users[query_user_id].last_edited_time_nanos = current_time
        return 0
    
    else:
        time_to_wait = (carte.timeout_nanos - (current_time - last_edited_time))*10**-9 # en secondes
        return {"error": f"Timeout not reached, need to wait {time_to_wait} seconds"}
