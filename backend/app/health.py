from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
def helath():
    return {"status": "ok"}
