from fastapi import APIRouter

router = APIRouter()


@router.get("/divisions")
def get_divisions():

    return {
        "message": "Divisions endpoint"
    }