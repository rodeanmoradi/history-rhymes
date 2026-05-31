def get_lesson_prompt(results, article):
    lesson_prompt = f"""You are a highly knowledgeable historian, journalist, and educator. Pick the article from the following list that 
    provides the most intriguing, perhaps unobvious, and intellectually rewarding historical parallel to the selected news headline. 
    Once you have done so, you must generate a lesson regarding this article's topic using your knowledge and the article. This lesson 
    should be written in a format that is engaging and keeps the reader entertained. It should not take more than one minute to read 
    through. 

    Articles 1: {results.matches[0].id}, 
    Abstract: {results.matches[0].metadata["abstract"]}, 

    Article 2: {results.matches[1].id}, 
    Abstract: {results.matches[1].metadata["abstract"]}, 

    Article 3: {results.matches[2].id}, 
    Abstract: {results.matches[2].metadata["abstract"]}, 

    Article 4: {results.matches[3].id},
    Abstract: {results.matches[3].metadata["abstract"]}, 
    
    Article 5: {results.matches[4].id}, 
    Abstract: {results.matches[4].metadata["abstract"]},

    Selected Headline: {article}"""

    return lesson_prompt