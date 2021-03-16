import feedparser
from dotenv import load_dotenv
import os
import re

# Import APIs
from sms_apis.sms_aws import SmsAws
from file_apis.file_local import FileLocal
from file_apis.file_aws import FileAws
from url_apis.url_tinyurl import UrlTinyurl

def stub_texted(config_data, texted_data):
    for mobile in config_data:
        if mobile not in texted_data:
            texted_data[mobile] = {
                'texts': 0
            }

        for rss_feed in config_data[mobile]:
            if rss_feed not in texted_data[mobile]:
                texted_data[mobile][rss_feed] = []


def text_posts(posts_to_text, texted_data):
    for post in posts_to_text:
        text_result = sms_client.send_sms(post)

        if text_result:
            # Track the texted URLs
            texted_data[post["mobile"]]["texts"] += 1
            texted_data[post["mobile"]][post["rss_url"]].append(post["link"])


def check_feeds(config_data, texted_data):
    posts_to_text = []

    for mobile in config_data:
        rss_urls = config_data[mobile]

        for rss_url in rss_urls:
            # Load the rss_feed
            rss_feed = feedparser.parse(rss_url)

            for post in rss_feed.entries:
                print(post['title'])
                keywords = config_data[mobile][rss_url]

                for keyword in keywords:
                    stripped_post = {
                        "title": post["title"],
                        "summary": post["summary"],
                        "link": post["link"],
                        "mobile": mobile,
                        "rss_url": rss_url,
                        "keyword": keyword.pattern,
                    }

                    # Check if keyword is in the post, but not already texted
                    if keyword.search(stripped_post["title"] + stripped_post["summary"]) and \
                            stripped_post["link"] not in texted_data[mobile][rss_url]:
                        posts_to_text.append(stripped_post)
                        break
    print(posts_to_text)
    return posts_to_text


def clean_posts(posts_to_text):
    for post in posts_to_text:
        alert_text = f'Alert: {post["keyword"]}'
        post["short_link"] = url_client.shorten_url(post["link"])
        title_chars = MAX_SMS_LENGTH - len(alert_text) - len(post["short_link"]) - 2

        if title_chars != len(post["title"]):
            # Title section was shortened
            post["title"] = post["title"][:title_chars - 3] + "..."

        post["message"] = f'{alert_text}\n{post["title"]}\n{post["short_link"]}'

    return posts_to_text


def main():
    # Assign APIs
    # sms_client = SmsAws()
    file_config = FileLocal()
    file_texted = FileLocal()
    # url_client = UrlTinyurl()

    # load_dotenv()
    # MAX_SMS_LENGTH = int(os.getenv("max_sms_length"))

    # if not MAX_SMS_LENGTH:
        # raise Exception("Missing max_sms_length from the environment.")

    # Load config
    initial_config = file_config.read_file_yaml("config.yml")
    regex_compiled_config = dict(initial_config)

    for number in initial_config.keys():
        for url in initial_config[number]:
            compiled_keywords = []
            for keyword in initial_config[number][url]:
                compiled_keywords.append(re.compile(keyword, re.IGNORECASE))
            regex_compiled_config[number][url] = compiled_keywords
    # Load texted
    # texted = file_texted.read_file_yaml("texted.yml")
    texted = dict()
    stub_texted(regex_compiled_config, texted)

    # Check for posts to text
    posts = check_feeds(regex_compiled_config, texted)

    # Prepare the posts for texting
    posts = clean_posts(posts)

    # Text the posts
    text_posts(posts, texted)

    # Update texted file
    file_texted.write_file_yaml("texted.yml", texted)


# Amazon Lambda Handler
def lambda_handler(event=None, context=None):
    main()

    return {
        'statuscode': 200,
        'body': 'success'
    }


if __name__ == "__main__":
    main()
