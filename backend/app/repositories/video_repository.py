from app.models import Camera, Frame, Video
from app.repositories.base import BaseRepository


class CameraRepository(BaseRepository[Camera]):
    model = Camera


class VideoRepository(BaseRepository[Video]):
    model = Video


class FrameRepository(BaseRepository[Frame]):
    model = Frame
