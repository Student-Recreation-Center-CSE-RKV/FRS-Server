from fastapi import FastAPI
from app.routes.index import router as main_router  
app = FastAPI()



app.include_router(main_router,prefix='/api')


# @app.get("/")
# async def home():
#     return await api()

# @app.get("/api")
# async def api():
#     temp = collection.find_one({})
#     print(temp)
#     return 