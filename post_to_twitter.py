import feedparser
import tweepy

# Enter your Twitter API keys here
consumer_key = 'your_consumer_key'
consumer_secret = 'your_consumer_secret'
access_token = 'your_access_token'
access_token_secret = 'your_access_token_secret'

# Authenticate with the Twitter API
auth = tweepy.OAuthHandler(consumer_key, consumer_secret)
auth.set_access_token(access_token, access_token_secret)
api = tweepy.API(auth)

# Enter the URL of your RSS feed here
rss_url = 'your_rss_url'

# Parse the RSS feed
feed = feedparser.parse(rss_url)

# Get the most recent entry
recent_entry = feed.entries[0]
tweet = recent_entry.title + "\n" + recent_entry.link

# Post the tweet
api.update_status(tweet)
