import streamlit as st
import pymongo
from pymongo import MongoClient
import random
import mysql.connector
from mysql.connector import Error
import time
from bson import ObjectId
import datetime
import sys
import os

cache_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'cache'))
checkpoint_file_path = os.path.join(cache_path, 'cache_checkpoint.json')
sys.path.append(cache_path)

import threading
from  clock_cache import ClockCache

# Initialize the ClockCache with the desired parameters
cache = ClockCache(capacity=500, checkpoint_file="cache.json", checkpoint_interval=30, ttl=None)

# Function to start periodic cache checkpointing in a separate thread
def start_cache_maintenance():
    cache.start_periodic_checkpoint()

# Start a separate thread for periodic cache checkpointing and purging stale entries
thread = threading.Thread(target=start_cache_maintenance, daemon=True)
thread.start()


# MongoDB connection
client = pymongo.MongoClient("mongodb+srv://nc913:twittersearch@cluster1.7k3fhrz.mongodb.net/")
db = client["twitter_database"]
tweets_collection = db["tweets_collection"]
retweets_collection = db["retweets_collection"]
replies_collection = db["replies_collection"]
quotes_collection = db["quotes_collection"]

# MySQL connection
connection = mysql.connector.connect(
    host="localhost",
    user="root",
    password="DbmsTeam#30",
    database="twitter_database"
)

def get_user_info_with_cache(user_id):
    key = f"user_{user_id}"
    result = cache.get(key)

    if result is None:
        result = get_user_info(user_id)
        cache.put(key, result)

    return result

def get_user_info(user_id):
    try:
        cursor = connection.cursor()
        query = f"SELECT screen_name, description, created_at_edt, followers_count FROM users WHERE id = {user_id}"
        cursor.execute(query)
        result = cursor.fetchone()

        if result:
            return {
                "screen_name": result[0],
                "description": result[1],
                "created_at_edt": result[2],
                "followers_count": result[3]
            }
        else:
            return None

    except Error as e:
        print(f"The error '{e}' occurred")
        return None
    

def get_user_tweets_with_cache(user_id, collection):
    key = f"user_{user_id}_{collection.name}"
    result = cache.get(key)
    if result is None:
        result = get_user_tweets(user_id, collection)
        cache.put(key, result)
    return result

def get_user_tweets(user_id, collection):
    query = {'user_id': int(user_id)}
    results_cursor = collection.find(query).sort('created_at_edt', pymongo.DESCENDING)
    results = []
    for doc in results_cursor:
        doc['_id'] = str(doc['_id'])  
        results.append(doc)
    return results




#neednot implement cache
def generate_user_tweet_html(tweet, user):
    """
    Generate an HTML representation of a tweet.

    Args:
    tweet (dict): The tweet information.
    user (dict): The user information.

    Returns:
    str: An HTML string representing the tweet.
    """
    tweet_html = f"""
    <div style="border: 1px solid #e1e8ed; border-radius: 4px; margin: 10px; padding: 10px; font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; font-size: 14px;">
        <div>
            <strong>{user['screen_name']}</strong> @{user['screen_name']} · {tweet['created_at_edt']}
        </div>
        <p style="margin-top: 10px;">{tweet['text']}</p>
        <div style="display: flex; justify-content: space-between; color: #657786; margin-top: 10px;">
            <span>{tweet['reply_count']}Replies</span>
            <span>{tweet['retweet_count']}Retweets</span>
            <span>{tweet['favorite_count']}Likes</span>
            <span>{tweet['source']}</span>
            <span>{tweet['hashtags']}Hashtags</span>
        </div>
    </div>
    """
    return tweet_html


def display_user_tweets(tweets, title):
    st.markdown(f"### {title}")
    for tweet in tweets:
        #user_info = get_user_info(tweet["user_id"])
        user_info = get_user_info_with_cache(tweet["user_id"])
        if user_info:
            tweet_html = generate_user_tweet_html(tweet, user_info)
            st.markdown(tweet_html, unsafe_allow_html=True)


def display_user_info(user_id, avatar_seed):
    #user = get_user_info(user_id)
    user = get_user_info_with_cache(user_id)
    if user:
        avatar_url = f"https://avatars.dicebear.com/api/avataaars/{avatar_seed}.svg"
        st.image(avatar_url, width=100)
        st.markdown(f"### {user['screen_name']} (@{user['screen_name']})")
        st.markdown(f"**Account created at:** {user['created_at_edt']}")
        st.markdown(f"**Followers count:** {user['followers_count']}")
        st.markdown(f"**Description:** {user['description']}")

        date_range = (start_epoch, end_epoch)
        
        tweets = get_user_tweets_with_cache(user_id, tweets_collection)
        #tweets = get_user_tweets(user_id, tweets_collection)
        #display_user_tweets(tweets, "Tweets", date_range)
        display_user_tweets(tweets, "Tweets")

        #quoted_tweets = get_user_tweets(user_id, quotes_collection)
        quoted_tweets = get_user_tweets_with_cache(user_id, quotes_collection)
        #display_user_tweets(quoted_tweets, "Quoted Tweets", date_range)
        display_user_tweets(quoted_tweets, "Quoted Tweets")


        #replies = get_user_tweets(user_id, replies_collection)
        replies = get_user_tweets_with_cache(user_id, replies_collection)
        #display_user_tweets(replies, "Replies", date_range)
        display_user_tweets(replies, "Replies")


    else:
        st.error("User information not found.")

#neednot implement cache
def generate_tweet_html(tweet, user):
    random_avatar = f"https://avatars.dicebear.com/api/avataaars/{tweet['avatar_seed']}.svg"
    tweet_html = f"""
    <a href="?user_id={tweet['user_id']}&avatar_seed={tweet['avatar_seed']}" style="text-decoration: none; color: inherit;">
        <div style="border: 1px solid #e1e8ed; border-radius: 4px; margin: 10px; padding: 10px; font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; font-size: 14px;">
            <div style="display: flex; align-items: center;">
                <img src="{random_avatar}" style="border-radius: 50%; width: 50px; height: 50px; margin-right: 10px;" />
                <div>
                    <strong>{user['screen_name']}</strong> @{tweet['user_id']} · {tweet['created_at_edt']}
                </div>
            </div>
            <p style="margin-top: 10px;">{tweet['text']}</p>
            <div style="display: flex; justify-content: space-between; color: #657786; margin-top: 10px;">
                <span>{tweet['reply_count']}Replies</span>
                <span>{tweet['retweet_count']}Retweets</span>
                <span>{tweet['favorite_count']}Likes</span>
                <span>{tweet['source']}</span>
                <span>{tweet['hashtags']}Hashtags</span>
            </div>
        </div>
    </a>
    """
    return tweet_html

def generate_user_html(user, avatar_seed):
    random_avatar = f"https://avatars.dicebear.com/api/avataaars/{avatar_seed}.svg"
    user_html = f"""
    <a href="?user_id={user['id']}&avatar_seed={avatar_seed}" style="text-decoration: none; color: inherit;">
        <div style="border: 1px solid #e1e8ed; border-radius: 4px; margin: 10px; padding: 10px; font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; font-size: 14px;">
            <div style="display: flex; align-items: center;">
                <img src="{random_avatar}" style="border-radius: 50%; width: 50px; height: 50px; margin-right: 10px;" />
                <div>
                    <strong>{user['screen_name']}</strong> @{user['id']} · {user['created_at_edt']} . {user['followers_count']} Followers
                </div>
            </div>
            <p style="margin-top: 10px;">{user['description']}</p>
        </div>
    </a>
    """
    return user_html

############################################################################################################
def get_all_users_with_cache(search_string, date_range):
    key = f"all_users_{search_string}_{date_range[0]}_{date_range[1]}"

    start_time_cached = time.time()
    result = cache.get(key)
    end_time_cached = time.time()
    cached_time = (end_time_cached - start_time_cached)*1000000


    if result is None:
        #st.write("Cache miss")
        result = get_all_users(search_string, date_range)
        cache.put(key, result)


    start_time_non_cached = time.time()
    get_all_users(search_string, date_range)
    end_time_non_cached = time.time()
    non_cached_time = (end_time_non_cached - start_time_non_cached)*1000

    col1, col2 = st.columns(2)
    col1.metric("Caching", f"{cached_time:.6f} μs")
    col2.metric("Without Caching", f"{non_cached_time:.6f} ms")


    return result 

def get_all_users(search_string, date_range):
    try:

        cursor = connection.cursor()
        query = f"""
        SELECT id, screen_name, description, created_at_edt, followers_count
        FROM users
        WHERE screen_name LIKE %s
        AND created_at_epoch >= %s
        AND created_at_epoch <= %s
        ORDER BY followers_count DESC
        """

        cursor.execute(query, (f"%{search_string}%", date_range[0], date_range[1]))
        results = cursor.fetchall()

        #st.wrtie(results)

        if results:
            users = []
            for result in results:
                users.append({
                    "id": result[0],
                    "screen_name": result[1],
                    "description": result[2],
                    "created_at_edt": result[3],
                    "followers_count": result[4]
                })
            return users
        else:
            return None

    except Error as e:
        print(f"The error '{e}' occurred")
        return None
    
def display_collection_helper_with_cache(query, collection, search_string, date_range):
    key = f"display_{collection.name}_{search_string}_{date_range[0]}_{date_range[1]}"

    start_time_cached = time.time()
    result = cache.get(key)
    end_time_cached = time.time()
    cached_time = (end_time_cached - start_time_cached)*1000000


    if result is None:
        #st.write("Cache miss")
        result = display_collection_helper(query, collection, search_string, date_range)
        cache.put(key, result)

    start_time_non_cached = time.time()
    display_collection_helper(query, collection, search_string, date_range)
    end_time_non_cached = time.time()
    non_cached_time = (end_time_non_cached - start_time_non_cached)*1000

    col1, col2 = st.columns(2)
    col1.metric("Caching", f"{cached_time:.6f} μs")
    col2.metric("Without Caching", f"{non_cached_time:.6f} ms")
    
    return result

def display_collection_helper(query, collection, search_string, date_range):
    results_cursor = collection.find(query).sort('retweet_count', pymongo.DESCENDING).limit(200)
    results = []
    for doc in results_cursor:
        doc['_id'] = str(doc['_id'])  # Convert ObjectId to string
        results.append(doc)
    return results


def display_collection(collection, search_string, date_range):
    query = {
        'text': {'$regex': search_string, '$options': 'i'},
        'created_at_epoch': {'$gte': date_range[0], '$lte': date_range[1]}
    }
    results = display_collection_helper_with_cache(query, collection, search_string, date_range)
    #results = collection.find(query).sort('retweet_count', pymongo.DESCENDING).limit(200)
    
    for tweet in results:
        tweet["avatar_seed"] = random.randint(1, 5000)
        #user_info = get_user_info(tweet["user_id"])
        user_info = get_user_info_with_cache(tweet["user_id"])
        if user_info:
            tweet_html = generate_tweet_html(tweet, user_info)
            st.markdown(tweet_html, unsafe_allow_html=True)

st.set_page_config(layout="wide")

#st.title('Twitter Search App')
st.markdown("<h1 style='text-align: center; color: white;'>Twitter Search App</h1>", unsafe_allow_html=True)
st.markdown("""
            <style>
            html, body, [class*="css"] {
                background-color: #1DA1F2 !important;
                color: white;  # Ensures text is visible against the blue background
            }
            footer {visibility: hidden;}
            </style>
            """, unsafe_allow_html=True)
hide_streamlit_style = """
            <style>
            footer {visibility: hidden;}
            </style>
            """



collection_filter = st.sidebar.selectbox('Top-Level Metrics', ['', 'Top 10 Users by followers', 'Top 10 Tweets by retweets', 'Top 10 Tweets by favorites', 'Top 10 Hashtags', 'Top Sources'])

def get_top_users_by_followers_with_cache(limit=10):
    key = f"top_users_{limit}"
    start_time_cached = time.time()
    result = cache.get(key)
    end_time_cached = time.time()
    cached_time = (end_time_cached - start_time_cached)*1000000
    if result is None:
        #st.write("Cache miss")
        result = get_top_users_by_followers(limit=10)
        cache.put(key, result)
    
    start_time_non_cached = time.time()
    get_top_users_by_followers(limit=10)
    end_time_non_cached = time.time()
    non_cached_time = (end_time_non_cached - start_time_non_cached)*1000

    col1, col2 = st.columns(2)
    col1.metric("Caching", f"{cached_time:.6f} μs")
    col2.metric("Without Caching", f"{non_cached_time:.6f} ms")

    # st.write(f"Execution time with caching: {cached_time:.6f} seconds")
    # st.write(f"Execution time without caching: {non_cached_time:.6f} seconds")

    return result

def get_top_users_by_followers(limit=10):
    # Function to get the top users by followers count
    try:
        cursor = connection.cursor()
        query = f"SELECT id, screen_name, description, created_at_edt, followers_count FROM users ORDER BY followers_count DESC LIMIT {limit}"
        cursor.execute(query)
        results = cursor.fetchall()

        if results:
            users = []
            for result in results:
                users.append({
                    "id": result[0],
                    "screen_name": result[1],
                    "description": result[2],
                    "created_at_edt": result[3],
                    "followers_count": result[4]
                })
            return users
        else:
            return None

    except Error as e:
        print(f"The error '{e}' occurred")
        return None

def display_top_users(users):
    # Function to display the top users
    for user in users:
        user["avatar_seed"] = random.randint(1, 5000)
        user_html = generate_user_html(user, user["avatar_seed"])
        st.markdown(user_html, unsafe_allow_html=True)


def get_top_tweets_by_metric_with_cache(metric, limit=10):
    key = f"top_tweets_{metric}_{limit}"
    start_time_cached = time.time()
    result = cache.get(key)
    end_time_cached = time.time()
    cached_time = (end_time_cached - start_time_cached)*1000000
    if result is None:
        #st.write("Cache miss")
        result = get_top_tweets_by_metric(metric, limit=10)
        cache.put(key, result)

    start_time_non_cached = time.time()
    get_top_tweets_by_metric(metric, limit=10)
    end_time_non_cached = time.time()
    non_cached_time = (end_time_non_cached - start_time_non_cached)*1000

    col1, col2 = st.columns(2)
    col1.metric("Caching", f"{cached_time:.6f} μs")
    col2.metric("Without Caching", f"{non_cached_time:.6f} ms")

    
    return result

def get_top_tweets_by_metric(metric, limit=10):
    # Function to get the top tweets based on the given metric
    query = {metric: -1}
    results_cursor = tweets_collection.find().sort(metric, pymongo.DESCENDING).limit(limit)
    results = []
    for doc in results_cursor:
        doc['_id'] = str(doc['_id'])  # Convert ObjectId to string
        results.append(doc)

    return results



def display_top_tweets(tweets):
    # Function to display the top tweets
    for tweet in tweets:
        tweet["avatar_seed"] = random.randint(1, 5000)
        #user_info = get_user_info(tweet["user_id"])
        user_info = get_user_info_with_cache(tweet["user_id"])
        if user_info:
            tweet_html = generate_tweet_html(tweet, user_info)
            st.markdown(tweet_html, unsafe_allow_html=True)



def display_top_hashtags_helper_with_cache(query, limit=10):
    key = f"top_hashtags_{limit}"
    start_time_cached = time.time()
    result = cache.get(key)
    end_time_cached = time.time()
    cached_time = (end_time_cached - start_time_cached)*1000000
    if result is None:
        #st.write("Cache miss")
        result = display_top_hashtags_helper(query, limit=10)
        cache.put(key, result)

    start_time_non_cached = time.time()
    display_top_hashtags_helper(query, limit=10)
    end_time_non_cached = time.time()
    non_cached_time = (end_time_non_cached - start_time_non_cached)*1000

    col1, col2 = st.columns(2)
    col1.metric("Caching", f"{cached_time:.6f} μs")
    col2.metric("Without Caching", f"{non_cached_time:.6f} ms")
    
    return result

def display_top_hashtags_helper(query, limit=10):
    results_cursor = tweets_collection.aggregate(query)
    results = []
    for doc in results_cursor:
        doc['_id'] = str(doc['_id'])  # Convert ObjectId to string
        results.append(doc)
    return results

def display_top_hashtags(limit=10):
    # Function to display the top hashtags
    query = [{"$unwind": "$hashtags"}, {"$group": {"_id": "$hashtags", "count": {"$sum": 1}}}, {"$sort": {"count": -1}}, {"$limit": limit}]
    results = display_top_hashtags_helper_with_cache(query, limit=10)
    #results = display_top_hashtags_helper(query, limit=10)
    #results = tweets_collection.aggregate(query)
    st.markdown("### Top 10 Hashtags")
    for result in results:
        st.markdown(f"{result['_id']} (Count: {result['count']})")


def display_top_sources_helper_with_cache(query ,limit=10):
    key = f"top_sources_{limit}"
    
    start_time_cached = time.time()
    result = cache.get(key)
    end_time_cached = time.time()
    cached_time = (end_time_cached - start_time_cached)*1000000

    if result is None:
        #st.write("Cache miss")
        result = display_top_sources_helper(query, limit=10)
        cache.put(key, result)


    start_time_non_cached = time.time()
    display_top_sources_helper(query, limit=10)
    end_time_non_cached = time.time()
    non_cached_time = (end_time_non_cached - start_time_non_cached)*1000

    col1, col2 = st.columns(2)
    col1.metric("Caching", f"{cached_time:.6f} μs")
    col2.metric("Without Caching", f"{non_cached_time:.6f} ms")

    return result

def display_top_sources_helper(query, limit=10):
    results_cursor = tweets_collection.aggregate(query)
    results = []
    for doc in results_cursor:
        doc['_id'] = str(doc['_id'])  # Convert ObjectId to string
        results.append(doc)
    return results

def display_top_sources(limit=10):
    # Function to display the top sources
    query = [{"$group": {"_id": "$source", "count": {"$sum": 1}}}, {"$sort": {"count": -1}}, {"$limit": limit}]
    results = display_top_sources_helper_with_cache(query, limit=10)
    #results = tweets_collection.aggregate(query)
    st.markdown("### Top Sources")
    for result in results:
        st.markdown(f"{result['_id']} (Count: {result['count']})")

# Call the functions based on the selected top-level metric
if collection_filter == 'Top 10 Users by followers':
    #top_users = get_top_users_by_followers()
    top_users = get_top_users_by_followers_with_cache()
    display_top_users(top_users)
elif collection_filter == 'Top 10 Tweets by retweets':
    #top_tweets = get_top_tweets_by_metric('retweet_count')
    top_tweets = get_top_tweets_by_metric_with_cache('retweet_count')
    display_top_tweets(top_tweets)
elif collection_filter == 'Top 10 Tweets by favorites':
    top_tweets = get_top_tweets_by_metric_with_cache('favorite_count')
    display_top_tweets(top_tweets)
elif collection_filter == 'Top 10 Hashtags':
    #display_top_hashtags()
    display_top_hashtags()
elif collection_filter == 'Top Sources':
    #display_top_sources()
    display_top_sources()

st.sidebar.header('Input')
string_search = st.sidebar.text_input('What do you want to search?')
collection_filter = st.sidebar.selectbox('Choose from which you want to search from', ['', 'Users', 'Tweets', 'Retweets', 'Quoted tweets', 'replies', 'Hashtags'])


# Add date range picker to the sidebar
#st.sidebar.header('Date Range')
#start_date = st.sidebar.date_input('Start date', value=datetime.date.today() - datetime.timedelta(days=30))
#end_date = st.sidebar.date_input('End date', value=datetime.date.today())

# Convert the selected date range to epoch time
#start_epoch = int(start_date.strftime('%s'))
#end_epoch = int((end_date + datetime.timedelta(days=1)).strftime('%s')) - 1

#date_range = (start_epoch, end_epoch)

st.sidebar.header('Date Range')
start_date = st.sidebar.date_input('Start date', value=datetime.date.today() - datetime.timedelta(days=3650))
end_date = st.sidebar.date_input('End date', value=datetime.date.today())

# Convert the selected date range to datetime at the beginning of the start date and the end of the end date
start_datetime = datetime.datetime.combine(start_date, datetime.time.min)
end_datetime = datetime.datetime.combine(end_date, datetime.time.max)

# Convert the selected date range to epoch time
start_epoch = int(start_datetime.timestamp())
end_epoch = int(end_datetime.timestamp())

date_range = (start_epoch, end_epoch)

query_params = st.query_params
selected_user_id = query_params.get("user_id", [None])[0]


def display_users(search_string, date_range):
    users = get_all_users_with_cache(search_string, date_range)
    #users = get_all_users(search_string, date_range)
    if users:
        for user in users:
            user["avatar_seed"] = random.randint(1, 5000)
            user_html = generate_user_html(user, user["avatar_seed"])
            st.markdown(user_html, unsafe_allow_html=True)
    else:
        st.write("No users found.")

def display_hashtags_helper_with_cache(query, collection, search_string, date_range):
    key = f"hashtags_{collection.name}_{search_string}_{date_range[0]}_{date_range[1]}"

    start_time_cached = time.time()
    result = cache.get(key)
    end_time_cached = time.time()
    cached_time = (end_time_cached - start_time_cached)*1000000
    if result is None:
        #st.write("Cache miss")
        result = display_hashtags_helper(query, collection, search_string, date_range)
        cache.put(key, result)

    start_time_non_cached = time.time()
    display_hashtags_helper(query, collection, search_string, date_range)
    end_time_non_cached = time.time()
    non_cached_time = (end_time_non_cached - start_time_non_cached)*1000

    col1, col2 = st.columns(2)
    col1.metric("Caching", f"{cached_time:.6f} μs")
    col2.metric("Without Caching", f"{non_cached_time:.6f} ms")

    return result

def display_hashtags_helper(query, collection, search_string, date_range):
    results_cursor = collection.find(query).sort('retweet_count', pymongo.DESCENDING).limit(200)
    results = []
    for doc in results_cursor:
        doc['_id'] = str(doc['_id'])  # Convert ObjectId to string
        results.append(doc)
    return results


def display_hashtags(collection, search_string, date_range):
    query = {
        'hashtags': {'$elemMatch': {'$regex': search_string, '$options': 'i'}},
        'created_at_epoch': {'$gte': date_range[0], '$lte': date_range[1]}
    }
    results = display_hashtags_helper_with_cache(query, collection, search_string, date_range)
    #results = collection.find(query).sort('retweet_count', pymongo.DESCENDING).limit(200)

    for tweet in results:
        tweet["avatar_seed"] = random.randint(1, 5000)
        #user_info = get_user_info(tweet["user_id"])
        user_info = get_user_info_with_cache(tweet["user_id"])
        if user_info:
            tweet_html = generate_tweet_html(tweet, user_info)
            st.markdown(tweet_html, unsafe_allow_html=True)

if selected_user_id:
    avatar_seed = query_params.get("avatar_seed", [None])[0]
    display_user_info(selected_user_id, avatar_seed)
else:
    if collection_filter == 'Tweets':
        #display_collection(tweets_collection, string_search, date_range)
        display_collection(tweets_collection, string_search, date_range)

    elif collection_filter == 'replies':
        #display_collection(replies_collection, string_search, date_range)
        display_collection(replies_collection, string_search, date_range)

    elif collection_filter == 'Retweets':
        #display_collection(retweets_collection, string_search, date_range)
        display_collection(retweets_collection, string_search, date_range)

    elif collection_filter == 'Quoted tweets':
        #display_collection(quotes_collection, string_search, date_range)
        display_collection(quotes_collection, string_search, date_range)

    elif collection_filter == 'Hashtags':
        display_hashtags(tweets_collection, string_search, date_range)

    elif collection_filter == 'Users':
        display_users(string_search, date_range)

    else:
        pass

    
