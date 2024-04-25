from datetime import date, datetime

from pydantic import BaseModel, Field


class PlayRequest(BaseModel):
    game: str = Field(..., description="Name of the game")
    playdate: str = Field(date.today().isoformat(), description="Date of the play")
    #  players: list = Field([], description="List of players")
    notes: str = Field("", description="Notes about the game")
    quantity: int = Field(1, description="Number of plays")
    length: int = Field(0, description="Length of the game in minutes")


class PlayPayload(BaseModel):
    playdate: str = Field(date.today().isoformat(), description="Date of the play")
    objectid: str = Field(..., description="BGG object id")
    length: int = Field(0, description="Length of the game in minutes")
    quantity: int = Field(1, description="Number of plays")
    comments: str = Field("", description="Comments about the game", alias="notes")
    location: str = Field("", description="Location of the play")
    action: str = "save"
    objecttype: str = "thing"
    ajax: int = 1
