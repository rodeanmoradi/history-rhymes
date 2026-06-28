def get_lesson_prompt(results, article):
    lesson_prompt = f"""
        You are a highly knowledgeable historian, journalist, and educator. Pick the article from the following list that 
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

        Selected Headline: {article}
    """

    return lesson_prompt

def get_search_prompt(article, description):

    if description is None:
        search_prompt = f"""
            Goal: find three historical parallel given current events. You are an expert historian, geopolitical intellectual, 
            and journalist. Given the below article, your task is to conduct deep research and find three parallel historical events. The events must
            be intriguing, at least somewhat significant, and may perhaps be unobvious. It is irrelevant when the events you have chosen took place.
            Once you choose the topics, provide summaries. These summaries must not exceed 100 words. Your output should ONLY contain the three
            topics and their summaries.
            
            Article: {article}
        """
    else:
        search_prompt = f"""
            Goal: find three historical parallel given a current event and its description. You are an expert historian, 
            geopolitical intellectual, and journalist. Given the below article, your task is to conduct deep research and find three parallel 
            historical events. The events must be intriguing, at least somewhat significant, and may perhaps be unobvious. It is irrelevant 
            when the events you have chosen took place. Once you choose the topics, provide summaries. These summaries must not exceed 100 words. 
            Your output should ONLY contain the three topics and their summaries.
            
            Article: {article}
            Description: {description}
        """

    return search_prompt

def get_eval_prompt(search_result, query_result):

    eval_prompt = f"""
        Goal: evaluate historical parallels. Given the historical topics below, evaluate them based on intellectual
        stimulation, intrigue, as well as (perhaps) being unobvious. Using this criteria, select one topic from the group. Once you have
        selected one topic, evaluate that one using the same criteria as before, but without comparing it to the others (evaluate it on its
        own merits). Upon evaluating the final chosen topic, if you find that it does not adhere to the criteria well enough (i.e it is not
        intellectually stimulating enough, intriguing enough, etc.), you may choose to conduct the topic search once more using the web
        search tool, query tool, or both.
        
        Topic 1: {query_result.matches[0].id}, 
        Abstract: {query_result.matches[0].metadata["abstract"]}, 

        Topic 2: {query_result.matches[1].id}, 
        Abstract: {query_result.matches[1].metadata["abstract"]},

        Topic 3: {query_result.matches[2].id}, 
        Abstract: {query_result.matches[2].metadata["abstract"]},

        Topic 4: {query_result.matches[3].id},
        Abstract: {query_result.matches[3].metadata["abstract"]},
        
        Topic 5: {query_result.matches[4].id}, 
        Abstract: {query_result.matches[4].metadata["abstract"]},

        Topics 6-8: {search_result.content[0].text}
    """
    
    return eval_prompt