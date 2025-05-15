from uuid import uuid4
from fastapi import Cookie, FastAPI, Query 
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

app = FastAPI()

app.add_middleware(CORSMiddleware, allow_origins=["*", "http://localhost:8000"], allow_credentials=True)

class User:
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.guesses = [] # liste des essais

class Wordle:
    def __init__(self, word_to_find: str):
        self.word_to_find = word_to_find
        self.users_guesses = {} # dictionnaire des essais pour chaque utilisateur
        self.keys = set()

    def create_new_user_id(self):
        user_id = str(uuid4())
        self.users_guesses[user_id] = User(user_id)
        return user_id
    
    def is_valid_user(self, user_id: str):
        return user_id in self.users_guesses
    
    def create_new_key(self):
        key = str(uuid4())
        self.keys.add(key)
        return key
    
    def is_valid_key(self, key: str):
        return key in self.keys

    def guess(self, word: str, user_id: str): # word est le mot proposé par l'utilisateur
        if not self.is_valid_user(user_id):
            return {"error": "Invalid user ID"}
        
        user = self.users_guesses[user_id]

        if len(user.guesses) >= 6:
            return {"error": "Maximum number of guesses reached"}
        
        if len(word) != 5:
            return {"error": "Word must be 5 letters long"}
        else:
            guess_color = [] # guess color est la liste des couleurs pour chaque lettre du mot proposé
            for i in range(5):
                if word[i] == self.word_to_find[i]:
                    guess_color.append("green")
                elif word[i] in self.word_to_find:
                    guess_color.append("yellow")
                else:
                    guess_color.append("gray")
            self.users_guesses[user].append(word)
            return {"result": (word, guess_color)}
        
word_to_find = "apple" # mot à trouver
wordles : dict[str, Wordle] = {
    "1": Wordle(word_to_find)
    } # dictionnaire des wordles en cours : chaque clef est le numéro de session et la valeur est le mot à trouver pour la session en cours
        
@app.get("/")
async def root():
    return {"message": "My Wordle"}

@app.get("/api/v1/{session}/preinit")
async def preinit(session: str):
    wordle = wordles[session]
    if not wordle in wordles:
        return JSONResponse({"error": "Session not found"}, status_code=404)
    
    key = wordle.create_new_key()
    res = JSONResponse({"key": key})
    res.set_cookie("key", key, secure= True, samesite="None", max_age=3600)
    return res
    

@app.get("/api/{session}/init")
async def init(session: str,
               query_key: str = Query(alias="key"),
               cookie_key: str = Cookie(alias="key")):
    wordle = wordles[session]

    if not wordle in wordles:
        return JSONResponse({"error": "Session not found"}, status_code=404)
    
    if query_key != cookie_key:
        return JSONResponse({"error": "Invalid key"}, status_code=403)
    
    if not wordle.is_valid_key(cookie_key):
        return JSONResponse({"error": "Invalid key"}, status_code=403)
    
    user_id = wordle.create_new_user_id()

    res = JSONResponse({"user_id": user_id})
    res.set_cookie("user_id", user_id, secure=True, samesite="None", max_age=3600)
    return res

@app.get("/api/{session}/guess")
async def guess(session: str,
                word: str,
                query_user_id: str = Query(alias="id"),
                cookie_key: str = Cookie(alias="key"),
                cookie_user_id: str = Cookie(alias="id")):
    wordle = wordles[session]

    if not wordle in wordles:
        return JSONResponse({"error": "Session not found"}, status_code=404)
    
    if query_user_id != cookie_user_id:
        return JSONResponse({"error": "User ID mismatch"}, status_code=403)
    
    if not wordle.is_valid_key(cookie_key):
        return JSONResponse({"error": "Invalid key"}, status_code=403)
    
    if not wordle.is_valid_user(cookie_user_id):
        return JSONResponse({"error": "Invalid user ID"}, status_code=403)
    
    result = wordle.guess(word, query_user_id)
    return result
