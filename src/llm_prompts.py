# All LLM prompts put here

LLM_PROMPT_CATEGORY_AND_RANKING_TPL = """
You are a content review expert, you can analyze how many topics in a content, and be able to calculate a quality score of them (range 0 to 1).

I’ll give u a content, and you will output a response with each topic, category and its score, and a overall score of the entire content.

You should only respond in JSON format as described below without any Explanation
Response format:
{{
  \"topics\": [ an array of dicts, each dict has 3 fields \"topic\", \"category\" and \"score\"],
  \"overall_score\": 0.9
}}

Double check before respond, ensure the response can be parsed by Python json.loads. The content is {content}
"""


LLM_PROMPT_CATEGORY_AND_RANKING_TPL2 = """
As an AI content reviewer, I need to assess the quality and categorize the user input text.

Constraints:
- Evaluate the quality of the text on a scale of 0 to 1, where 0 represents poor quality and 1 represents excellent quality.
- Classify the content into relevant topics and assign ONE category from the PREDEFINED list below.
- Consider grammar, coherence, factual accuracy, and overall readability while assessing the quality.
- Give higher scores to articles that reflect new trends and developments in global economic and technological macro-level dynamics.
- Ensure objectivity and impartiality in the evaluation.

PREDEFINED CATEGORIES (you MUST choose from these only):
1. "Paper" - Academic papers, research papers, arxiv papers, scientific publications
2. "AI/ML" - Artificial Intelligence, Machine Learning, Deep Learning, LLM, NLP, Computer Vision
3. "Tech Industry" - Technology company news, product launches, industry trends
4. "Engineering" - Software engineering, programming, development tools, DevOps, system design
5. "Security" - Cybersecurity, privacy, hacking, vulnerabilities, compliance
6. "Business" - Business strategy, company news, startup news
7. "Economy" - Economics, finance, markets, investment, stock, crypto
8. "Science" - Scientific discoveries, research findings (non-AI/ML)
9. "Product" - Product reviews, tools, applications, user experience
10. "Career" - Career advice, personal development, workplace culture
11. "Other" - Content that doesn't fit the above categories

IMPORTANT RULES:
- If the content is from arxiv.org or is an academic/research paper, category MUST be "Paper"
- Each topic should have exactly ONE category from the predefined list
- Give the top 3 most relevant topics

You should only respond in JSON format. Do not write any explanation outside the JSON.
Response format:
{{
  \"feedback\": "[brief feedback]",
  \"topics\": [ an array of dicts, each dict has 2 fields \"topic\", \"category\"],
  \"overall_score\": [Score from 0 to 1]
}}

Double check: ensure each category is from the predefined list and response can be parsed by Python json.loads.

The user input text: {content}
"""


LLM_PROMPT_SUMMARY_COMBINE_PROMPT = """
Write a concise summary of the following text delimited by triple backquotes.
Summarize the main points and their comprehensive 
explanations from below text, presenting them under appropriate headings. 
Use various Emoji to symbolize different sections, and format the content as a cohesive paragraph under each heading. 
Ensure the summary is clear, detailed, and informative, reflecting the executive summary style found in news articles. 
Avoid using phrases that directly reference 'the script provides' to maintain a direct and objective tone.


```{text}```
NUMBERED LIST SUMMARY:
"""


# With translation (Notes: use with suffix together)
LLM_PROMPT_SUMMARY_COMBINE_PROMPT2 = """
Write a concise summary of the following text delimited by triple backquotes.
Summarize the main points and their comprehensive 
explanations from below text, presenting them under appropriate headings. 
Use various Emoji to symbolize different sections, and format the content as a cohesive paragraph under each heading. 
Ensure the summary is clear, detailed, and informative, reflecting the executive summary style found in news articles. 
Avoid using phrases that directly reference 'the script provides' to maintain a direct and objective tone.

```{text}```
"""

LLM_PROMPT_SUMMARY_COMBINE_PROMPT2_SUFFIX = """
NUMBERED LIST SUMMARY IN BOTH ENGLISH AND {}, AFTER FINISHING ALL ENGLISH PART, THEN FOLLOW BY {} PART, USE '===' AS THE SEPARATOR:
"""

LLM_PROMPT_SUMMARY_COMBINE_PROMPT3 = """
As an expert analyst, extract and summarize the core ideas and most valuable insights from the following text. Use Markdown formatting.

Guidelines:
- Start with a brief mention of the source/publication if identifiable from the text
- Extract key innovations, breakthroughs, or novel perspectives
- Highlight implications for global economic trends, technological developments, or scientific progress
- Include actionable insights or strategic takeaways
- Cite specific data, statistics, or concrete examples that support the main arguments
- Note any counterintuitive findings or paradigm-shifting ideas
- Explain WHY this article might interest the reader (e.g., emerging trends, investment opportunities, career implications, or industry disruption)
- Use **bold** for key terms and important points
- Use separate paragraphs for different sections

Avoid:
- Generic descriptions or background information that adds no value
- Repetitive or redundant points
- Surface-level observations without depth

Output Format (use Markdown):
## [Source: XXX]

**Why Read This:** [Brief explanation]

### Key Insights

1. **[Key Point 1]**: [Explanation]

2. **[Key Point 2]**: [Explanation]

... (3-7 points total, each substantive and insightful)

Content to analyze:
```{text}```
"""

LLM_PROMPT_SUMMARY_COMBINE_PROMPT4 = """
As a professional summarizer, create a concise and comprehensive summary of the provided text, be it an article, post, conversation, or passage, while adhering to these guidelines:
- Craft a summary that is detailed, thorough, in-depth, and complex, while maintaining clarity and conciseness.
- Incorporate main ideas and essential information, eliminating extraneous language and focusing on critical aspects.
- Rely strictly on the provided text, without including external information.
- Format the summary in paragraph form for easy understanding, and use the numbered list as the output format:
{text}
"""

LLM_PROMPT_SUMMARY_COMBINE_PROMPT_SUFFIX = """
NUMBERED LIST SUMMARY IN BOTH ENGLISH AND {}, AFTER FINISHING ALL ENGLISH PART, THEN FOLLOW BY {} PART, USE '===' AS THE SEPARATOR:
"""

# One-liner summary
LLM_PROMPT_SUMMARY_ONE_LINER = """
Write a concise and precise one-liner summary of the following text without losing any numbers and key points (English numbers need to be converted to digital numbers):
{text}
"""

LLM_PROMPT_JOURNAL_PREFIX = """
You have a series of random journal notes that need refinement and rewriting without altering their original meaning.

Your goal is to:
- Make the journal entry more cohesive, polished, and organized while preserving the essence of the original content.
"""

# In case need a translation
LLM_PROMPT_JOURNAL_MIDDLE = """
- For all the above goals, write one English version, then translate it to {} (including insights, takeaways, and action items), and use === as the delimiter.
"""

LLM_PROMPT_JOURNAL_SUFFIX = """
Before responding to the output, review it carefully and make sure it meets all the above goals.

Take the provided notes below and craft a well-structured journal entry:
{content}
"""

LLM_PROMPT_TRANSLATION = """
Translate the below content into {}:
"""

# Direct target language summary (no English, no separator)
LLM_PROMPT_SUMMARY_TARGET_LANG = """
As an expert analyst, extract and summarize the core ideas and most valuable insights from the following text. Write your summary in {} using Markdown formatting.

Guidelines:
- Start with a brief mention of the source/publication if identifiable from the text
- Extract key innovations, breakthroughs, or novel perspectives
- Highlight implications for global economic trends, technological developments, or scientific progress
- Include actionable insights or strategic takeaways
- Cite specific data, statistics, or concrete examples that support the main arguments
- Note any counterintuitive findings or paradigm-shifting ideas
- Explain WHY this article might interest the reader (e.g., emerging trends, investment opportunities, career implications, or industry disruption)
- Use **bold** for key terms and important points
- Use separate paragraphs for different sections

Avoid:
- Generic descriptions or background information that adds no value
- Repetitive or redundant points
- Surface-level observations without depth

Output Format (use Markdown):
## [Source: XXX]

**Why Read This:** [Brief explanation in {}]

### Key Insights

1. **[Key Point 1]**: [Explanation]

2. **[Key Point 2]**: [Explanation]

... (3-7 points total, each substantive and insightful)

Content to analyze:
```{{text}}```
"""

# Generate title in target language
LLM_PROMPT_TITLE_TARGET_LANG = """
Generate a concise, SEO-optimized title in {} (at most 15 words) for the following content. Output ONLY the title, nothing else:
{{content}}
"""

LLM_PROMPT_TITLE = """
Generate a concise SEO-optimized 'Title', which is at most eight words for the below content:
{content}
"""

LLM_PROMPT_ACTION_ITEM = """
Analyze the user input content carefully and generate concise 'Action Items' at most eight words:
- DO NOT generate 'action item' unless necessary.
- Please carefully review and avoid generating duplicated 'action items'.
- If no action items can be found, return "None" as the response.

Response format:
1. Learn new language start from today
2. Buy a coffee from Shop
3. Have a chat with Bob this afternoon

The user input text: {content}
"""

LLM_PROMPT_KEY_INSIGHTS = """
Analyze the below content carefully and generate concise 'Critical Insights':
{content}
"""

LLM_PROMPT_TAKEAWAYS = """
Analyze the below content carefully and generate concise 'Takeaways':
{content}
"""

LLM_PROMPT_SUMMARY_SIMPLE = """
Analyze the below content carefully and generate concise 'Summary':
{content}
"""

LLM_PROMPT_SUMMARY_SIMPLE2 = """
Analyze the below content carefully and generate concise 'Summary' without losing any numbers, and English numbers need to convert to digital numbers:
{content}
"""

######################################################################
# AUTOGEN
######################################################################
AUTOGEN_COLLECTOR = """
Information Collector. For the given query, collect as much information as possible. You can get the data from the web search or Arxiv, then scrape the content; After collect all information, add TERMINATE to the end of the report.
"""

AUTOGEN_COLLECTOR2 = """
Information Collector. For the given query, do a research on that.
You can search from Internet to get top 3 most relevant articles and search papers from Arxiv, then scrape the content to generate detailed research report with loads of technique details and all reference links attached.
After collect all information, add TERMINATE to the end of the report.
"""

AUTOGEN_EDITOR = """
You are a senior Editor.
- You will define the structure based on the user's query and the provided material, then give it to the Writer to write the article.
- Make sure have a 'References' section at the bottom.
- After sending the structure to the writer, then stop replying.
"""

AUTOGEN_EDITOR2 = """
You are a senior Editor.
- You will define the structure based on the user's query, then give it to the Writer to write the article.
- Make sure have a 'References' section at the bottom.
- After sending the structure to the writer, then stop replying.
"""

# Parameter: {topic}
AUTOGEN_EDITOR3 = """
You are a professional Editor.
- You will define the most relevant structure based on the user query '{}', then give it to the Writer to write the article.
- Make sure have a 'References' section at the bottom.
- After sending the structure to the writer, then stop replying.
"""

AUTOGEN_WRITER = """
You are a professional blogger.
You will write an article with in-depth insights based on the structure provided by the Editor and the material provided.
According to the feedback from the Checker or Reviewer, reply with the refined article.
"""

AUTOGEN_WRITER2 = """
You are an essay writer. You will need to do a detailed research the user's query, formulate a thesis statement, and create a persuasive piece of work that is both informative, detailed and engaging.
- Your writing needs to follow the structure provided by the Editor, and leverage the relevant information from material provided as much as possible, AND DO NOT use the irrelevant information from the materials.
- Emphasize the importance of statistical evidence, research findings, and concrete examples to support your narrative.
According to the feedback from the Reviewer and the potential additional information provided, please explain the changes one by one with the reasoning first, then reply with the refined article.
"""

# Parameter: {topic}
AUTOGEN_WRITER3 = """
You are an AI writer tasked with creating a comprehensive article on '{}'.
The user has provided some initial materials, including key points, relevant data, and specific themes they want addressed in the article.
Your goal is to leverage this information and the Editor defined structure, generate an informative and engaging article.
Ensure that your content aligns with the user's expectations and incorporates the provided materials seamlessly.
If there are any uncertainties or gaps in the user-provided information, feel free to seek clarification or suggest alternatives.
You can ask for diagram/screenshot, just add [screenshot] to where you think there should be one and I will add those later.
Make sure there will be a 'References' section at the bottom, and withall reference links attached.
According to the feedback from the Checker or Reviewer, focuing on REVISE the content by the most relevant information provided, DO NOT comment on the feedback, just reply with the latest full refined article.
"""

AUTOGEN_WRITER4 = """
You are a professional blogger. You will need to do a detailed research the user's query, formulate a thesis statement, and create a persuasive piece of work that is both informative, detailed and engaging.
Your writing needs to follow the structure provided by the Editor, and leverage the relevant information from the material provided.
Emphasize the importance of statistical evidence, research findings, and concrete examples and numbers to support your narrative.
According to the feedback from the Reviewer and the potential additional information provided, please explain the changes one by one with the reasoning first, then reply with the refined article.
"""

AUTOGEN_REVIEWER = """
You are a world-class blog content critic, you will review and critique the given article content (not the structure) and provide feedback to the Writer.
- Critically assess the content, structure, and overall quality of the article.
- If the content is missing the details, gaps or low-quality, leverage functions to search from Internet or search papers from Arxiv, then scrape to improve it.
- Reply 'ALL PASSED' if everything looks great. Otherwise, provide the feedback to the writer.
- After at most 15 rounds of reviewing iterations with the Writer, stop the review, and pass the latest full refined article from the Writer to the Publisher.
"""

AUTOGEN_REVIEWER2 = """
You are a world-class blog content critic, you will review and critique the given article content (not the structure) and provide feedback to the Writer.
- Critically assess the content, structure, and overall quality of the article.
- If there are any uncertainties, gaps, or low-quality part in the article, feel free to leverage functions to search from Internet and search papers from Arxiv, then send back to Writer for the further improvement.
- After at most 15 rounds of reviewing iterations with the Writer, stop the review, and send the latest full refined article to the Publisher.
"""

AUTOGEN_REVIEWER3 = """
You are a world-class blog content critic, you will review and critique the given article content (not the structure) and provide feedback to the Writer.
Critically assess the content, structure, and overall quality of the article, and offer specific suggestions for improvement and highlight both strengths and weaknesses. Ensure your feedback is detailed and geared towards enhancing the article's clarity, rigor, and impact within the field.
After 2 rounds of reviewing iterations with the Writer, stop the review, and ask for the latest full refined article from the Writer, then pass it to the Publisher.
"""

AUTOGEN_PUBLISHER = """
Publisher. After reviewer's review, ask for the latest full refined article, then save the article to a file.
"""

AUTOGEN_PUBLISHER2 = """
Publisher. You will get the article after the Reviewer's review, then save the article to a file.
"""

# Parameter: {topic}
AUTOGEN_DEEPDIVE_COLLECTION = """
Collect information for the topic: '{}'
"""

# Parameter: {topic}, {user-provided materials}
AUTOGEN_DEEPDIVE_ARTICLE = """
Write an article for the user's query and the user has provided some initial materials.

User's query: {}

User-Provided Materials:
{}
"""

# AUTOGEN additional iteration prompt
# Parameter: {topic}, {article}, {user-provided materials}
AUTOGEN_DEEPDIVE_FOLLOWUP = """
Refine the article below based on the user query, and the user has provided the draft and some initial materials, improve the article with more details, examples and numbers to support:

User's query: {}

User drafted article: {}

User-Provided Materials: {}

"""

######################################################################
# DAILY DIGEST
######################################################################
LLM_PROMPT_DAILY_DIGEST = """
You are a professional news editor creating a daily briefing. Analyze the news items and create a structured digest.

Guidelines:
- Synthesize information across all sources to identify key themes
- Focus on actionable insights and significant developments
- Group related news items together
- Highlight cross-cutting trends that appear in multiple sources
- Use **bold** for emphasis on key terms and important points

Output Format (use Markdown):

## Daily News Digest

**Executive Summary:** [2-3 sentences highlighting the most important developments of the day]

### Key Events
[Significant announcements, product launches, breaking news - bullet points]

### Market & Industry Trends
[Patterns, market movements, emerging trends - bullet points]

### Notable Developments
[Interesting insights, research findings, things worth watching - bullet points]

### What to Watch
[2-3 specific action items or things to monitor going forward]

---
*Sources: {source_count} articles from {source_names}*

Content to analyze:
{content}
"""

LLM_PROMPT_DAILY_DIGEST_TARGET_LANG = """
You are a professional news editor creating a daily briefing in {target_lang}. Analyze the news items and create a structured digest.

Guidelines:
- Synthesize information across all sources to identify key themes
- Focus on actionable insights and significant developments
- Group related news items together
- Highlight cross-cutting trends that appear in multiple sources
- Use **bold** for emphasis on key terms and important points
- Write the entire output in {target_lang}

Output Format (use Markdown):

## Daily News Digest

**Executive Summary:** [2-3 sentences highlighting the most important developments of the day]

### Key Events
[Significant announcements, product launches, breaking news - bullet points]

### Market & Industry Trends
[Patterns, market movements, emerging trends - bullet points]

### Notable Developments
[Interesting insights, research findings, things worth watching - bullet points]

### What to Watch
[2-3 specific action items or things to monitor going forward]

---
*Sources: {{source_count}} articles from {{source_names}}*

Content to analyze:
{{content}}
"""

LLM_PROMPT_DAILY_DIGEST_TITLE = """
Generate a concise, engaging title (at most 10 words) for this daily news digest. The title should capture the main theme or most important topic of the day. Output ONLY the title, nothing else:
{content}
"""

LLM_PROMPT_DAILY_DIGEST_TITLE_TARGET_LANG = """
Generate a concise, engaging title in {target_lang} (at most 10 words) for this daily news digest. The title should capture the main theme or most important topic of the day. Output ONLY the title, nothing else:
{{content}}
"""
