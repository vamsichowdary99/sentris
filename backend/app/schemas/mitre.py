from app.schemas.common import ORMModel


class MitreTechniqueRead(ORMModel):
    id: str
    name: str
    tactic: str
    description: str
    url: str
