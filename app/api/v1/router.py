from fastapi import APIRouter

from app.api.v1 import account, export, plan, regenerate, trips

router = APIRouter(prefix="/api/v1")
router.include_router(plan.router)
router.include_router(regenerate.router)
router.include_router(export.router)
router.include_router(trips.router)
router.include_router(account.router)
