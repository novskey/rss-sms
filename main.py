import yaml
import feedparser
import boto3
from dotenv import load_dotenv
import os


def load_config():
    with open("config.yml") as file:
        config_data = yaml.load(file, Loader=yaml.FullLoader)

    return config_data


def load_texted():
    with open("texted.yml") as file:
        texted_data = yaml.load(file, Loader=yaml.FullLoader)

    if not texted_data:
        texted_data = {}

    return texted_data


def stub_texted(config_data, texted_data):
    for mobile in config_data:
        if mobile not in texted_data:
            texted_data[mobile] = {
                'texts': 0
            }

            for rss_feed in config_data[mobile]:
                texted_data[mobile][rss_feed] = []


def text_post(mobile, post, sms_client):
    sms_message = f'Alert {post["keyword"]}\n{post["title"]}\n{post["link"]}'

    if len(sms_message) > 160:
        # TODO: Optimisations around character length
        print(f"Too many characters..\n{sms_message}")
        return False

    sms_res = sms_client.publish(
        PhoneNumber=mobile,
        Message=sms_message,
        Subject="RSS SMS"
    )

    return sms_res


def check_feeds(config_data, texted_data, sms_client):
    for mobile in config_data:
        print(f"Scanning for {mobile}")
        rss_urls = config_data[mobile]

        posts_to_text = []

        for rss_url in rss_urls:
            # Load the rss_feed
            print(f"loading rss feed {rss_url}")

            rss_feed = feedparser.parse(rss_url)

            for post in rss_feed.entries:
                keywords = config_data[mobile][rss_url]

                for keyword in keywords:
                    keyword = keyword.lower()
                    stripped_post = {
                        "title": post["title"],
                        "summary": post["summary"],
                        "link": post["link"],
                        "rss_url": rss_url,
                        "keyword": keyword,
                    }

                    # Check if keyword is in the post, but not already texted
                    if (keyword in stripped_post["title"].lower() or
                        keyword in stripped_post["summary"].lower()) and \
                            stripped_post["link"] not in texted_data[mobile][rss_url]:
                        posts_to_text.append(stripped_post)
                        break

        print(posts_to_text)

        # Text the deals to the mobile
        print(f"Texting {mobile} {len(posts_to_text)} posts")
        for post in posts_to_text:
            print(text_post(mobile, post, sms_client))

        # Track the texted URLs
        texted_data[mobile]["texts"] = texted_data[mobile]["texts"] + len(posts_to_text)

        for texted_post in posts_to_text:
            texted_data[mobile][texted_post["rss_url"]].append(texted_post["link"])

    pass


def update_texted(texted_data):
    with open("texted.yml", "w") as file:
        yaml.dump(texted_data, file)


def aws_client():
    load_dotenv()

    aws_access_key_id = os.getenv("aws_access_key_id")
    aws_secret_access_key = os.getenv("aws_secret_access_key")
    aws_region_name = os.getenv("aws_region_name")

    # Create SNS client
    sns_client = boto3.client(
        "sns",
        aws_access_key_id=aws_access_key_id,
        aws_secret_access_key=aws_secret_access_key,
        region_name=aws_region_name
    )

    return sns_client


if __name__ == "__main__":
    # Create sms client
    client = aws_client()

    # Load config
    config = load_config()
    print(config)

    # Load texted
    texted = load_texted()
    stub_texted(config, texted)
    print(texted)
    print()

    # Go through each mobile, each URL and search the most recent posts for each keyword
    check_feeds(config, texted, client)

    # Update the texted file
    update_texted(texted)
