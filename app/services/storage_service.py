from sqlalchemy.orm import Session
from app.models import Division


async def save_division(
    db: Session,
    division_number: int,
    division_name: str
):

    division = Division(
        division_number=division_number,
        division_name=division_name
    )

    db.add(division)
    db.commit()
    db.refresh(division)

    return division