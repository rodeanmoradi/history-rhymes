from typing import Literal

from pydantic import BaseModel, Field

from app.agents import PipelineError, create
from app.config import LESSON_EFFORT
from app.prompts import LESSON_SYSTEM, get_lesson_prompt

# The drawing vocabulary. static/sketch.js knows how to draw every value listed here,
# so keep the two in sync when adding a pose, hat or prop.
Pose = Literal["stand", "walk", "run", "point", "cheer", "think", "shrug", "sit", "kneel", "fall", "fight", "hold", "wave"]
Hat = Literal["none", "crown", "helmet", "bicorne", "tophat", "cap", "laurel", "hood", "turban"]
Spot = Literal["left", "center_left", "center", "center_right", "right"]
PropKind = Literal[
    "ship", "boat", "castle", "tower", "wall", "house", "tent", "factory", "throne", "desk", "flag",
    "cannon", "shield", "coins", "scroll", "barrel", "sack", "tree", "hill", "sun", "cloud", "crowd",
    "chart_up", "chart_down", "ballot_box", "train", "rocket",
]


class Figure(BaseModel):
    label: str = Field(description="Short name shown under the figure, or empty")
    pose: Pose
    hat: Hat
    spot: Spot
    facing: Literal["left", "right"]
    size: Literal["small", "normal", "big"]
    says: str = Field(description="Speech bubble text, at most eight words, or empty")


class Prop(BaseModel):
    kind: PropKind
    spot: Spot
    label: str = Field(description="Short label, or empty")


class Scene(BaseModel):
    setting: Literal["land", "sea", "city", "indoors"]
    figures: list[Figure]
    props: list[Prop]
    caption: str


class Section(BaseModel):
    heading: str
    body: str = Field(description="60 to 110 words")
    scene: Scene


class ThenNow(BaseModel):
    then: str
    now: str


class Lesson(BaseModel):
    title: str = Field(description="A plain, specific title, like a chapter heading")
    dek: str = Field(description="One or two sentences connecting the headline to the event")
    sections: list[Section]
    then_and_now: list[ThenNow]
    where_it_breaks: str = Field(description="A short paragraph on the important differences")
    takeaway: str
    further_reading: list[str] = Field(description="Exact English Wikipedia article titles")


def gather_material(choice, evidence):
    parts = []
    if choice["archive_title"]:
        article = evidence.archive[choice["archive_title"]]
        parts.append(f"Wikipedia, \"{article['title']}\":\n{article['abstract']}")
    for title, article in evidence.archive.items():
        if title != choice["archive_title"] and choice["parallel"].lower() in article["abstract"].lower():
            parts.append(f"Wikipedia, \"{title}\":\n{article['abstract']}")
    parts.extend(f"Web research notes:\n{text}" for text in evidence.web_texts)
    return "\n\n".join(parts) or "(none; rely on well-established facts only)"


def problems(lesson):
    """Schema-valid output can still be degenerate (we've seen one section and "x" for every other field)."""
    found = []
    if not 3 <= len(lesson.sections) <= 4:
        found.append(f"{len(lesson.sections)} sections")
    if len(lesson.then_and_now) < 2:
        found.append("missing then-and-now")
    texts = [lesson.dek, lesson.where_it_breaks, lesson.takeaway]
    texts += [s.body for s in lesson.sections] + [s.scene.caption for s in lesson.sections]
    if not lesson.title.strip() or any(len(t.split()) < 3 for t in texts):
        found.append("placeholder text")
    if any(not s.scene.figures and not s.scene.props for s in lesson.sections):
        found.append("empty scene")
    return found


def write_lesson(headline, choice, evidence, trace, attempts=2):
    prompt = get_lesson_prompt(headline, choice, gather_material(choice, evidence))
    for attempt in range(attempts):
        response = create(
            trace, "write_lesson",
            parse=True,
            max_tokens=16000,
            system=LESSON_SYSTEM,
            output_config={"effort": LESSON_EFFORT},
            output_format=Lesson,
            messages=[{"role": "user", "content": prompt}],
        )
        lesson = response.parsed_output
        found = problems(lesson)
        if not found:
            return lesson.model_dump()
    raise PipelineError(f"write_lesson: unusable lesson after {attempts} attempts ({', '.join(found)})")
