import praw
import re
import pandas as pd
from textblob import TextBlob
from datetime import datetime
import uuid
import os
from urllib.parse import urlparse

# Initialize Reddit API client (replace with your credentials)
reddit = praw.Reddit(
    client_id="_Q9JA97AMegqKBsapVxxXw",
    client_secret="NlFznG1cN0xB2a3Tg81-wVQqIC5MXw",
    user_agent="Reddit Persona Scraper by /u/Rahul Rai"
)

def extract_username_from_url(profile_url):
    """Extract username from Reddit profile URL."""
    parsed_url = urlparse(profile_url)
    path = parsed_url.path.strip('/')
    username = path.split('/')[-1]
    return username

def scrape_user_data(username):
    """Scrape posts and comments for a given Reddit user."""
    try:
        redditor = reddit.redditor(username)
        # Initialize data structures
        posts_data = []
        comments_data = []

        # Scrape posts (submissions)
        for submission in redditor.submissions.new(limit=50):
            posts_data.append({
                'id': submission.id,
                'title': submission.title,
                'body': submission.selftext,
                'subreddit': submission.subreddit.display_name,
                'score': submission.score,
                'created_utc': datetime.utcfromtimestamp(submission.created_utc),
                'permalink': f"https://www.reddit.com{submission.permalink}"
            })

        # Scrape comments
        for comment in redditor.comments.new(limit=50):
            comments_data.append({
                'id': comment.id,
                'body': comment.body,
                'subreddit': comment.subreddit.display_name,
                'score': comment.score,
                'created_utc': datetime.utcfromtimestamp(comment.created_utc),
                'permalink': f"https://www.reddit.com{comment.permalink}"
            })

        return posts_data, comments_data
    except Exception as e:
        print(f"Error scraping data for {username}: {e}")
        return [], []

def analyze_content(posts, comments):
    """Analyze posts and comments to build user persona."""
    persona = {
        'interests': [],
        'personality_traits': [],
        'expertise_level': [],
        'demographics': [],
        'engagement_style': []
    }
    citations = []

    # Combine posts and comments for analysis
    all_content = [(item, 'post') for item in posts] + [(item, 'comment') for item in comments]

    # Extract interests (based on subreddits)
    subreddits = set(item[0]['subreddit'] for item in all_content)
    for subreddit in subreddits:
        related_items = [(item[0]['permalink'], item[1]) for item in all_content if item[0]['subreddit'] == subreddit]
        persona['interests'].append(f"Active in r/{subreddit}")
        citations.append({
            'characteristic': f"Interest: Active in r/{subreddit}",
            'references': [item[0] for item in related_items],
            'type': 'subreddit'
        })

    # Analyze personality traits (sentiment analysis)
    for item, item_type in all_content:
        text = item['body'] if item['body'] else item.get('title', '')
        if not text:
            continue
        blob = TextBlob(text)
        sentiment = blob.sentiment.polarity
        if sentiment > 0.2:
            trait = "Positive tone"
        elif sentiment < -0.2:
            trait = "Critical or negative tone"
        else:
            trait = "Neutral tone"
        if trait not in persona['personality_traits']:
            persona['personality_traits'].append(trait)
            citations.append({
                'characteristic': f"Personality: {trait}",
                'references': [item['permalink']],
                'type': item_type
            })

    # Infer expertise level (based on content complexity and subreddit context)
    for item, item_type in all_content:
        text = item['body'] if item['body'] else item.get('title', '')
        if not text:
            continue
        word_count = len(text.split())
        technical_terms = len(re.findall(r'\b(technical|expert|advanced|specialized)\b', text, re.IGNORECASE))
        if word_count > 100 or technical_terms > 0:
            level = f"Knowledgeable in r/{item['subreddit']}"
            if level not in persona['expertise_level']:
                persona['expertise_level'].append(level)
                citations.append({
                    'characteristic': f"Expertise: {level}",
                    'references': [item['permalink']],
                    'type': item_type
                })

    # Engagement style (based on interaction frequency and scores)
    total_items = len(all_content)
    avg_score = sum(item[0]['score'] for item in all_content) / total_items if total_items > 0 else 0
    if total_items > 30:
        style = "Highly active contributor"
    elif total_items > 10:
        style = "Moderately active contributor"
    else:
        style = "Occasional contributor"
    persona['engagement_style'].append(style)
    citations.append({
        'characteristic': f"Engagement: {style}",
        'references': [item[0]['permalink'] for item in all_content[:5]],  # Cite up to 5 items
        'type': 'aggregate'
    })

    # Demographics (limited inference, e.g., from explicit mentions)
    for item, item_type in all_content:
        text = item['body'] if item['body'] else item.get('title', '')
        if re.search(r"\b(I am|I'm)\s(a|an)\s(\w+)", text, re.IGNORECASE):
            match = re.search(r"\b(I am|I'm)\s(a|an)\s(\w+)", text, re.IGNORECASE).group(3)
            persona['demographics'].append(f"Self-identified as {match}")
            citations.append({
                'characteristic': f"Demographic: Self-identified as {match}",
                'references': [item['permalink']],
                'type': item_type
            })

    return persona, citations

def write_persona_to_file(username, persona, citations):
    """Write user persona to a text file with citations."""
    output_dir = "reddit_personas"
    os.makedirs(output_dir, exist_ok=True)
    filename = f"{output_dir}/{username}_persona.txt"

    with open(filename, 'w', encoding='utf-8') as f:
        f.write(f"User Persona for Reddit User: {username}\n")
        f.write("=" * 50 + "\n\n")

        for category, traits in persona.items():
            if traits:
                f.write(f"{category.replace('_', ' ').title()}:\n")
                for trait in traits:
                    f.write(f"- {trait}\n")
                    # Find citations for this trait
                    for citation in citations:
                        if citation['characteristic'].lower().startswith(category.lower()) and trait in citation['characteristic']:
                            f.write("  Citations:\n")
                            for ref in citation['references']:
                                f.write(f"    - {ref} ({citation['type'].title()})\n")
                f.write("\n")

    print(f"Persona written to {filename}")

def main():
    profile_url = input("Enter Reddit user profile URL: ")
    username = extract_username_from_url(profile_url)
    print(f"Scraping data for user: {username}")

    posts, comments = scrape_user_data(username)
    if not posts and not comments:
        print("No data retrieved. Check the username or API credentials.")
        return

    persona, citations = analyze_content(posts, comments)
    write_persona_to_file(username, persona, citations)

if __name__ == "__main__":
    main()