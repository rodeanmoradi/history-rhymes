def get_search_prompt(headline, description):
    angle = f"\nAngle to pursue: {description}" if description else ""
    return f"""Search the web to find three historical events that parallel this news headline. Start by searching for
the story itself so you understand what actually happened, then search for parallels. Prefer parallels that are
surprising and instructive over the obvious ones; any period or place is fine, but each must be a real, well-documented
event. For each, give its name, its date, and a summary of at most 80 words that makes the parallel clear. Output only
the three events.

Headline: {headline}{angle}"""


AGENT_SYSTEM = """You choose the historical parallel for a news headline. The reader will get a short illustrated lesson about
the event you pick, so it has to be worth their time:
- The mechanism should genuinely rhyme with the headline (the same incentives, pressures or mistakes), not just share a keyword.
- A less obvious parallel beats a famous one if it fits as well.
- It must be a real, well-documented event.

You start with candidates from two sources: a curated archive of Wikipedia history articles, and open web research. If none
of them is good enough, search again with search_archive or research_web, describing the underlying mechanism (e.g. "naval
blockade forcing economic collapse") rather than repeating the headline's words. You can call both tools in the same turn.
You get at most two rounds of searching.

When you have chosen, reply with the JSON object. If the event is one of the archive articles, set archive_title to that
article's exact title; otherwise leave archive_title empty."""


def get_agent_prompt(headline, archive_results, web_results):
    return f"""Headline: {headline}

Archive results:
{archive_results}

Web research:
{web_results}"""


def get_choice_prompt(headline, candidates, source):
    # Single-source baselines used by the eval: same chooser, no tools, one pool of candidates.
    return f"""Headline: {headline}

Candidates ({source}):
{candidates}

Choose the best parallel from these candidates only, and reply with the JSON object."""


LESSON_SYSTEM = """You write the lessons for a website that pairs today's news with a parallel from history. Each lesson is
read in about two minutes and illustrated with simple stick-figure panels.

How to write:
- Plain, concrete prose in the manner of a good history teacher or a well-edited newspaper. Names, dates, places, numbers.
- Tell what happened in order, and let the parallel emerge from the facts. Don't announce that history repeats itself.
- Short paragraphs. No rhetorical questions, no exclamation marks, no lists inside the body text.
- Avoid stock phrases: "in a world where", "little did they know", "fast forward", "a cautionary tale", "delve",
  "tapestry", "testament to", "echoes of history".
- Only state facts you are confident of. If the sources disagree or a detail is uncertain, leave it out.
- Be honest about where the parallel breaks down; that section matters as much as the similarities.

How to draw (one scene per section):
- Each scene shows one moment from that section, literally, like a quick sketch in a schoolbook margin.
- One to three figures and up to three props. Label the people who matter with a short name ("Pericles", "Spartans").
- Speech is optional and short (at most eight words). Dry humour is welcome; jokes about suffering are not.
- Use "big" for the powerful side in a scene and "small" for the weak or for crowds in the distance.
- The caption is a plain sentence describing the moment, like a figure caption in a textbook."""


def get_lesson_prompt(headline, choice, material):
    return f"""Today's headline: {headline}

Chosen parallel: {choice['parallel']} ({choice['era']}, {choice['place']})
Why it was chosen: {choice['why']}
Where it breaks down: {choice['where_it_breaks']}

Source material:
{material}

Write the lesson: three or four sections telling the story of {choice['parallel']}, then three then-and-now
comparisons, the honest differences, and a one-sentence takeaway. List the Wikipedia article titles a curious reader
should open next under further_reading."""
