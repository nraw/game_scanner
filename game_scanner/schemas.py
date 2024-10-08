from datetime import date
from typing import Optional

from pydantic import BaseModel, Field, validator


class PlayRequest(BaseModel):
    game: str = Field(..., description="Name of the game")
    playdate: str = Field(
        default_factory=lambda: date.today().isoformat(),
        description="Date of the play in the format YYYY-MM-DD",
    )
    #  players: list = Field([], description="List of players")
    notes: str = Field("", description="Notes about the game")
    quantity: int = Field(1, description="Number of plays")
    length: int = Field(0, description="Length of the game in minutes")


class PlayPayload(BaseModel):
    playdate: str = Field(
        default_factory=lambda: date.today().isoformat(),
        description="Date of the play in the format YYYY-MM-DD",
    )
    objectid: str = Field(..., description="BGG object id", alias="game_id")
    length: int = Field(0, description="Length of the game in minutes")
    quantity: int = Field(1, description="Number of plays")
    comments: str = Field("", description="Comments about the game", alias="notes")
    location: str = Field("", description="Location of the play")
    action: str = "save"
    objecttype: str = "thing"
    ajax: int = 1

    @validator("objectid", pre=True)
    def convert_to_str(cls, v):
        return str(v)


class LogRequest(BaseModel):
    game_id: int = Field(..., description="BoardGameGeek of the game")
    playdate: str = Field(
        default_factory=lambda: date.today().isoformat(),
        description="Date of the play in the format YYYY-MM-DD",
    )
    #  players: list = Field([], description="List of players")
    notes: str = Field("", description="Notes about the game")
    quantity: int = Field(1, description="Number of plays")
    length: int = Field(0, description="Length of the game in minutes")


class WishlistRequest(BaseModel):
    game_id: int = Field(..., description="BoardGameGeek of the game")


class BGGIdReuqest(BaseModel):
    game: str = Field(..., description="Name of the game")


class MyGamesFilter(BaseModel):
    player_count: Optional[int] = Field(..., description="Number of players")


class LogDeletionRequest(BaseModel):
    play_id: int = Field(..., description="ID of the play to delete")


class LogsFilter(BaseModel):
    game_ids: Optional[list] = Field(None, description="List of BoardGameGeek IDs")
    last_n: Optional[int] = Field(
        None, description="Number of logs to return. Format YYYY-MM-DD"
    )
    since: Optional[str] = Field(None, description="Filter logs before this date")
