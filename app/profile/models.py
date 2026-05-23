from pydantic import BaseModel, Field


class PhysicalTraits(BaseModel):
    height_cm: int
    build: str
    hair_color: str
    eye_color: str


class ActorProfile(BaseModel):
    name: str
    age: int
    gender: str
    languages: list[str] = Field(default_factory=list)
    physical: PhysicalTraits
    skills: list[str] = Field(default_factory=list)
    experience_level: str
    union_status: str
    location: str
    max_travel_km: int = 100
    availability_from: str
    role_preferences: dict[str, float] = Field(default_factory=dict)

    def to_summary(self) -> str:
        skills_str = ", ".join(self.skills) if self.skills else "none listed"
        langs_str = ", ".join(self.languages)
        prefs = ""
        if self.role_preferences:
            top = sorted(self.role_preferences.items(), key=lambda x: x[1], reverse=True)[:5]
            prefs = f"\nRole preferences (learned): {', '.join(f'{k} ({v:+.1f})' for k, v in top)}"
        return (
            f"Name: {self.name}, Age: {self.age}, Gender: {self.gender}\n"
            f"Languages: {langs_str}\n"
            f"Physical: {self.physical.height_cm}cm, {self.physical.build} build, "
            f"{self.physical.hair_color} hair, {self.physical.eye_color} eyes\n"
            f"Skills: {skills_str}\n"
            f"Experience: {self.experience_level}, Union: {self.union_status}\n"
            f"Location: {self.location} (max {self.max_travel_km}km travel)\n"
            f"Available from: {self.availability_from}"
            f"{prefs}"
        )
