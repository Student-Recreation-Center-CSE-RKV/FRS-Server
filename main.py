from fastapi import Depends,FastAPI,HTTPException,status
from fastapi.security import OAuth2PasswordBearer,OAuth2PasswordRequestForm
from pydantic import BaseModel
from datetime import datetime,timedelta
from jose import JWTError,jwt
from passlib.context import CryptContext

SECRET_KEY="db9c2516a45ba1440ab9bc243c1b0c0648348f60a2c83150ba79207801447a38"
ALGORITHM="HS256"
ACCESS_TOKEN_EXPIRE_MINUTES=30



db={
    "student1":{
        #For checking here I used password student123
        "username":"student1",
        "email":"student1@rguktrkv.ac.in",
        "hashed_password":"$2b$12$r5ZUNTy/vdNECiIr8JpWdu1T9bXkg7HL.8rqhpyIBd20wU2Bl4/ga",
        "disabled":False
          
    }
}
class Token(BaseModel):
    access_token:str
    token_type:str

class TokenData(BaseModel):
    username: str or None=None
class User(BaseModel):
    username:str or None=None
    email:str or None=None
    disabled: bool or None=None
    
class UserIndb(User):
    hashed_password:str
    
pwd_context=CryptContext(schemes=["bcrypt"],deprecated="auto")
oauth2_scheme=OAuth2PasswordBearer(tokenUrl="token")

app=FastAPI(docs_url="/docs")

def verify_password(plain_password,hashed_password):
    return pwd_context.verify(plain_password,hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def get_user(db,username: str):
    if username in db:
        user_data=db[username]
        return UserIndb(**user_data) #Here ** is used to fetch all the data of user form db as username=value like in dict we have : but here it  retrieves in for of =

def authenticate_user(db,username:str,password:str):
    user=get_user(db,username)
    if not user:    
        return False
    if not verify_password(password,user.hashed_password):
        return False
    return user

def create_access_token(data:dict,expires_delta:timedelta or None=None):
    to_encode=data.copy() #Using copy because it will not alter original data if any changes made
    if expires_delta:
        expire=datetime.utcnow()+expires_delta
    else:
        expire=datetime.utcnow()+timedelta(minutes=15)
    to_encode.update({"exp":expire})
    encoded_jwt=jwt.encode(to_encode,SECRET_KEY,algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(token:str=Depends(oauth2_scheme)):#This will take token and parse it
    credentials_exception=HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,detail="Could not Validate credentials",headers={"WWW-Authenticate":"Bearer"})
    try:
        payload=jwt.decode(token,SECRET_KEY,algorithms=[ALGORITHM])
        username:str=payload.get("sub")
        if username is None:
            raise credentials_exception
            
        token_data=TokenData(username=username)
        
    except JWTError:
        raise credentials_exception
    
    user=get_user(db,username=token_data.username)
    if user is None:
        raise credentials_exception
    return user

async def get_current_active_user(current_user:UserIndb =Depends(get_current_user)):
    if current_user.disabled:
        raise HTTPException(status_code=400,detail="Inactive User")
    return current_user

@app.post("/token",response_model=Token)
async def login_for_access_token(form_data:OAuth2PasswordRequestForm =Depends()):
    user =authenticate_user(db,form_data.username,form_data.password)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,detail="Incorrect Username or Password",headers={"WWW-Authenticate":"Bearer"})
    access_token_expires=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token=create_access_token(data={"sub":user.username},expires_delta=access_token_expires)
    return {"access_token":access_token,"token_type":"bearer"}

@app.get("/users/me/",response_model=User)
async def read_users_me(current_user:User =Depends(get_current_active_user)):
    return current_user

@app.get("/users/me/items")
async def read_own_items(current_user:User =Depends(get_current_active_user)):
   return [{"item_is":1,"owner":current_user}]


