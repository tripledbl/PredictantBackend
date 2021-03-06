from extensions import mongo_client
from square.client import Client
from bson.objectid import ObjectId
from .config import *
import pandas as pd
from datetime import datetime


# the number of groups of orders to retrieve from square APIs
# each group has a limit of 500 orders
NUM_ORDER_GROUPS = 100


# retrieve_square_orders_data
# inputs: none
# output: a json dataset of the data from the square orders API
def retrieve_square_orders_data(user_id):
    # get database access to get the square access token
    keystore_collection = mongo_client.db.KeyStore
    key = keystore_collection.find_one({'_id': ObjectId(user_id)})
    user_access_token = key['square_access_token']

    # create square sdk client
    client = Client(
        square_version='2021-10-20',
        access_token=user_access_token,
        environment='production'
    )

    order_count_collection = mongo_client.db.OrderCounts

    cursor = None
    cursor_count = NUM_ORDER_GROUPS
    # hashmap for storing order dates and counts
    order_counts = {}
    # boolean for checking if older order dates have been found
    older_dates_found = False

    # finds the most recent date in the database
    try:
        most_recent_date = (order_count_collection.find({}, {'datetime': 1}).sort([('datetime', -1)]).limit(1))[0]['datetime']
    except:
        most_recent_date = None

    # # For testing MOST_RECENT_DATE and skips first week
    # result = client.orders.search_orders(
    #     body={
    #         'location_ids': [
    #             LOCATION_ID
    #         ],
    #         'cursor': cursor
    #     }
    # )
    #
    # cursor = result.body['cursor']

    while cursor_count != 0:
        # made call to square orders API
        result = client.orders.search_orders(
            body={
                'location_ids': [
                    LOCATION_ID
                ],
                'cursor': cursor
            }
        )
        if result.is_success():
            # iterate through each order object
            for order in result.body['orders']:
                # get the date of the order as a datetime object
                try:
                    order_datetime = datetime.strptime(order['created_at'], '%Y-%m-%dT%H:%M:%SZ')
                except:
                    order_datetime = datetime.strptime(order['created_at'], '%Y-%m-%dT%H:%M:%S.%fZ')

                # Setting H, M, S, and MS to 0 because we only want date and MongoDB doesn't accept date
                order_datetime = order_datetime.replace(hour=0, minute=0, second=0, microsecond=0)

                # Checking if date is already in db to reduce redundancy
                if most_recent_date is not None and most_recent_date >= order_datetime:
                    older_dates_found = True
                    break

                # if the date already exists in the dictionary then increment its count
                if order_datetime in order_counts:
                    order_counts[order_datetime] = order_counts[order_datetime] + 1
                # if the date does not yet exist in the dictionary then create it and set its count to 1
                else:
                    order_counts[order_datetime] = 1

            # if other older order dates are found then stop adding redundant orders to db
            if older_dates_found:
                break

            # update the cursor for the next group of orders
            try:
                cursor = result.body['cursor']
            except:
                break

        else:
            return result.is_error()

        cursor_count = cursor_count - 1

    for key, value in order_counts.items():
        order_count_collection.insert_one({
            'datetime': key,
            'order_count': value,
        })

    return result.body


# orders_to_dataframe
# inputs: None
# outputs: converts order count data in mongodb into a dataframe with columns (date, order_count)
def orders_to_dateframe():

    # set up client for order count collection
    order_count_collection = mongo_client.db.OrderCounts

    # initialize a dataframe with the given columns
    df = pd.DataFrame(columns=['date', 'order_count'])

    # iterate though each item in the order count collection
    for order_count in order_count_collection.find():
        # add each order count in the collection into the dataframe
        df.loc[len(df)] = [order_count['datetime'], order_count['order_count']]

    return df

# add_date_columns
# inputs: a dataframe with an input that is a datetime
# outputs: multiple columns are added to the dataframe regarding the datetime column and all of the related DateTimeIndex methods
def add_date_columns(df):
    # cast the orders column to an integer
    df['order_count'] = pd.to_numeric(df['order_count'])

    # add columns for the relevant date features
    df['year'] = pd.DatetimeIndex(df['date']).year
    df['month'] = pd.DatetimeIndex(df['date']).month
    df['day'] = pd.DatetimeIndex(df['date']).day
    df['dayofyear'] = pd.DatetimeIndex(df['date']).dayofyear
    df['weekofyear'] = pd.DatetimeIndex(df['date']).weekofyear
    df['weekday'] = pd.DatetimeIndex(df['date']).weekday
    df['quarter'] = pd.DatetimeIndex(df['date']).quarter
    df['is_month_start'] = pd.DatetimeIndex(df['date']).is_month_start
    df['is_month_end'] = pd.DatetimeIndex(df['date']).is_month_end

    # remove the date column because we dont need it anymore
    df = df.drop(['date'], axis=1)

    # dummy encoding technique to create categorical variables from necessary columns
    df = pd.get_dummies(df, columns=['year'], prefix='year')
    df = pd.get_dummies(df, columns=['month'], prefix='month')
    df = pd.get_dummies(df, columns=['weekday'], prefix='wday')
    df = pd.get_dummies(df, columns=['quarter'], prefix='qrtr')
    df = pd.get_dummies(df, columns=['is_month_start'], prefix='m_start')
    df = pd.get_dummies(df, columns=['is_month_end'], prefix='m_end')

    return df
