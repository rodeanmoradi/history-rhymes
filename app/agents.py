import time
from concurrent.futures import ThreadPoolExecutor

from pydantic import BaseModel

from app.config import AGENT_EFFORT, BETAS, FALLBACKS, MODEL, SEARCH_EFFORT, anthropic_client
from app.prompts import AGENT_SYSTEM, get_agent_prompt, get_choice_prompt, get_search_prompt
from app.retrieval import format_results, search_archive

MAX_SEARCH_ROUNDS = 2


class PipelineError(Exception):
    pass


class Candidate(BaseModel):
    name: str
    era: str
    reason: str


class Choice(BaseModel):
    parallel: str
    era: str
    place: str
    archive_title: str
    why: str
    where_it_breaks: str
    runners_up: list[Candidate]


def create(trace, step, parse=False, **kwargs):
    """One Claude call with refusal fallback, recorded in the trace. parse=True validates output_format."""
    messages_api = anthropic_client().beta.messages
    method = messages_api.parse if parse else messages_api.create
    start = time.monotonic()
    response = method(model=MODEL, betas=BETAS, extra_body=FALLBACKS, **kwargs)
    trace.add_message(step, response, time.monotonic() - start)
    if response.stop_reason == "refusal":
        raise PipelineError(f"{step}: the model declined this headline")
    if response.stop_reason == "max_tokens":
        raise PipelineError(f"{step}: response was cut off at max_tokens")
    return response


def research_web(headline, description, trace):
    """Open-ended web research for three parallels. Returns {"text", "sources"}."""
    messages = [{"role": "user", "content": get_search_prompt(headline, description)}]
    tools = [{"type": "web_search_20260209", "name": "web_search", "max_uses": 3}]
    while True:
        response = create(
            trace, "research_web",
            max_tokens=16000,
            output_config={"effort": SEARCH_EFFORT},
            messages=messages,
            tools=tools,
        )
        if response.stop_reason != "pause_turn":
            break
        messages.append({"role": "assistant", "content": response.content})

    text = "\n".join(block.text for block in response.content if block.type == "text").strip()
    sources = []
    for block in response.content:
        if block.type == "web_search_tool_result" and isinstance(block.content, list):
            sources.extend({"title": r.title, "url": r.url} for r in block.content)
    return {"text": text, "sources": sources}


TOOLS = [
    {
        "name": "search_archive",
        "description": (
            "Semantic search over a curated archive of Wikipedia history articles. The description is what gets "
            "embedded, so phrase it as the themes and mechanism you want (e.g. \"naval blockade forcing economic "
            "collapse\") rather than the headline's literal words. Returns the top 5 article titles with the start of "
            "each abstract. Coverage is limited to what is in the archive."
        ),
        "strict": True,
        "input_schema": {
            "type": "object",
            "properties": {
                "description": {
                    "type": "string",
                    "description": "Up to ten words naming the themes or mechanism to search for",
                }
            },
            "required": ["description"],
            "additionalProperties": False,
        },
    },
    {
        "name": "research_web",
        "description": (
            "Open-ended live web research that returns three candidate historical parallels with short summaries. "
            "Slower and more expensive than search_archive, but not limited to the archive."
        ),
        "strict": True,
        "input_schema": {
            "type": "object",
            "properties": {
                "description": {
                    "type": "string",
                    "description": "Up to 25 words on the deeper themes and mechanism the parallel should share",
                }
            },
            "required": ["description"],
            "additionalProperties": False,
        },
    },
]


class Evidence:
    """Everything the agent saw, kept so the lesson writer can be grounded in it."""

    def __init__(self):
        self.archive = {}
        self.web_texts = []
        self.web_sources = []

    def add_archive(self, results):
        for r in results:
            self.archive.setdefault(r["title"], r)

    def add_web(self, research):
        self.web_texts.append(research["text"])
        self.web_sources.extend(research["sources"])


def run_tool(name, description, headline, evidence, trace):
    if name == "search_archive":
        results = search_archive(description, trace=trace)
        evidence.add_archive(results)
        return format_results(results)
    if name == "research_web":
        research = research_web(headline, description, trace)
        evidence.add_web(research)
        return research["text"]
    raise PipelineError(f"unknown tool {name}")


def choose(messages, trace, step, tools=None):
    kwargs = {"tools": tools} if tools else {}
    return create(
        trace, step,
        parse=True,
        max_tokens=16000,
        system=AGENT_SYSTEM,
        output_config={"effort": AGENT_EFFORT},
        output_format=Choice,
        messages=messages,
        **kwargs,
    )


def find_parallel(headline, trace, on_step=lambda message: None, mode="agentic"):
    """Pick the historical parallel for a headline.

    mode="agentic": archive + web candidates, then the agent may search again (the production pipeline).
    mode="archive" / "web": one source of candidates and no follow-up searches (baselines for the eval).
    """
    evidence = Evidence()

    on_step("Searching the archive and the web for candidates")
    with ThreadPoolExecutor(max_workers=2) as pool:
        archive_job = pool.submit(search_archive, headline, trace=trace) if mode != "web" else None
        web_job = pool.submit(research_web, headline, None, trace) if mode != "archive" else None
        if archive_job:
            evidence.add_archive(archive_job.result())
        if web_job:
            evidence.add_web(web_job.result())

    archive_text = format_results(list(evidence.archive.values()))
    web_text = evidence.web_texts[0] if evidence.web_texts else ""

    if mode == "archive":
        messages = [{"role": "user", "content": get_choice_prompt(headline, archive_text, "archive articles")}]
    elif mode == "web":
        messages = [{"role": "user", "content": get_choice_prompt(headline, web_text, "web research")}]
    else:
        messages = [{"role": "user", "content": get_agent_prompt(headline, archive_text, web_text)}]

    tools = TOOLS if mode == "agentic" else None
    on_step(f"Weighing {len(evidence.archive) + 3 * len(evidence.web_texts)} candidates")

    rounds = 0
    while True:
        response = choose(messages, trace, "choose", tools)
        if response.stop_reason != "tool_use":
            break
        if rounds >= MAX_SEARCH_ROUNDS:
            raise PipelineError("agent kept searching past its budget")
        rounds += 1

        calls = [block for block in response.content if block.type == "tool_use"]
        for call in calls:
            where = "archive" if call.name == "search_archive" else "web"
            on_step(f"Searching the {where} again: “{call.input['description']}”")

        with ThreadPoolExecutor(max_workers=len(calls)) as pool:
            jobs = [
                pool.submit(run_tool, c.name, c.input["description"], headline, evidence, trace) for c in calls
            ]
            results = []
            for call, job in zip(calls, jobs):
                try:
                    results.append({"type": "tool_result", "tool_use_id": call.id, "content": job.result()})
                except PipelineError:
                    raise
                except Exception as e:
                    results.append(
                        {"type": "tool_result", "tool_use_id": call.id, "content": f"Error: {e}", "is_error": True}
                    )

        if rounds >= MAX_SEARCH_ROUNDS:
            results.append({"type": "text", "text": "That was your last search. Choose now."})
        messages.append({"role": "assistant", "content": response.content})
        messages.append({"role": "user", "content": results})

    choice = response.parsed_output
    if choice is None:
        raise PipelineError("agent did not return a choice")
    choice = choice.model_dump()
    if choice["archive_title"] not in evidence.archive:
        choice["archive_title"] = ""
    on_step(f"Chose: {choice['parallel']}")
    return choice, evidence
