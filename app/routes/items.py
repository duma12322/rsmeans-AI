from fastapi import APIRouter

router = APIRouter()


@router.get("/items/{division_id}")
def get_items(division_id: int):

    return {
        "division": division_id
    }