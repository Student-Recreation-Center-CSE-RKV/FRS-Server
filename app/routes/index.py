from fastapi import APIRouter
from app.routes.v1.index  import router as routers_v1

router = APIRouter()


router.include_router(routers_v1 , prefix="/v1")