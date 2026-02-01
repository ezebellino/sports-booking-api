from fastapi import APIRouter # type: ignore

router = APIRouter(tags=["health"])

@router.get("/health")
def health():
    return {"status": "está todo ok"}
