import pandas as pd
import numpy as np


def change_to_date(df, cols):
    """
    Converts values in columns to datetime objects.

    Args:
        df (DataFrame): dataframe
        cols (list): list of columns
    """

    df[cols] = df[cols].apply(pd.to_datetime, errors="coerce")
    return df

def parse_zipcode(df, cols=["ORIGIN_3DIGIT_ZIP", "DESTINATION_3DIGIT_ZIP"], new_cols=["ORIGIN_CITY", "DESTINATION_CITY"]):

    from postalcodes_ca import fsa_codes
    import json


    def parse_zipcode_(zipcode):
        """
        Converts three digit zipcode to city or state.

        Args:
            zipcode (str): first three digits or letters of American zipcode or Canadian postal code
            cols (str): names of the columns to parse zipcodes
            new_cols (str): names of new columns that will contain the city names


        Returns:
            DataFrame: updated DataFrame
        """
        # covnerts zipcode to string
        if not isinstance(zipcode, str): zipcode = str(zipcode)

        if zipcode in zipcode_dict: # checks if zipcode is in America
            nearby = zipcode_dict[zipcode] # the nearest metropolitan
            return nearby["city"] + " " + nearby["state"]
        else:
            try: # checks if zipcode appears in Canadian zipcodes
                nearby = fsa_codes.get_nearby(zipcode, radius=1)[0] # the nearest metropolitan
                return nearby.name + " " + nearby.province
                
            except:
                return np.nan

    # reads in US zipcode dictionary
    with open("../data/threeDigitZipCodes.json") as json_file:
        zipcode_dict = json.load(json_file)

    # parses one column at a time
    for col, new_col in zip(cols, new_cols):
        df[new_col] = df[col].apply(lambda zipcode: parse_zipcode_(zipcode))

    return df

def flatten_ref_num(df, col="REFERENCE_NUMBER"):
    """
    Flattens dataframe by expanding a column with list values into multiple rows.

    Args:
        df (DataFrame): dataframe to flatten
        cols (_type_): columns to flatten
    """

    if col=="REFERENCE_NUMBER": 
        # REFERENCE_NUMBER column has a unique pattern of list elements where \n exists between every item
        df[col] = df[col].apply(lambda lst: lst.split("\"")[1::2])

    # create an individual row for each value in REFERENCE_NUMBER
    df = df.explode(col).reset_index(drop=True)

    return df

def join_offers_orders(offers, orders, on="REFERENCE_NUMBER"):
    """
    Returns a table with each offer paired with its order

    Args:
        offers (DataFrame): offers table
        orders (DataFrame): orders table
    """

    return pd.merge(offers, orders, how="left", on=on)

def get_remaining_time(df, past="CREATED_ON_HQ", future="PICKUP_DEADLINE_PST", new_col="REMAINIG_TIME"):
    """
    Calculates remaining delivery time from when an offer is made.

    Args:
        df (DataFrame): a merged dataset of offeres and orders
        past (str): name of column that stores later time information. Defaults to "CREATED_ON_HQ".
        future (str): name of column that stores earlier time information. Defaults to "PICKUP_DEADLINE_PST".
        new_col (str): name of column to store the remaining time. Defaults to "REMAINIG_TIME".

    """

    df["REMAINIG_TIME"] = df[future] - df[past]

    return df

def during_business_hours(df):
    """
    Adds a column that shows whether an offer was made during business hours.

    Args:
        df (DataFrame): DataFrame to study
    """

    hours = df["CREATED_ON_HQ"].dt.hour
    hours = ((hours >= 8) | (hours <= 18))

    days = df["CREATED_ON_HQ"].dt.dayofweek
    days = days < 5

    during_business_hours = hours & days

    df["BUSINESS_HOURS"] = during_business_hours

    return df

def get_prorated_rate(df, delivered_only=False):
    """
    Calculates prorated cost of pooled offers.

    Args:
        df (DataFrame): DataFrame to perform calculations on
        delivered_only (boolean): whether to filter for only offers that were chosen

    """
    # filters for pooled offers
    pooled = df[df["OFFER_TYPE"]=="pool"].reset_index(drop=True).drop("OFFER_TYPE", axis=1)

    # filters for delivered offers
    if delivered_only:
        pooled = pooled[pooled["LOAD_DELIVERED_FROM_OFFER"]].reset_index(drop=True).drop("LOAD_DELIVERED_FROM_OFFER", axis=1)

    # assigns unique value to each offer for future data aggregation purposes
    pooled["OFFER_ID"] = pooled["CARRIER_ID"] + " " + pooled["CREATED_ON_HQ"].apply(lambda x: str(x))

    # records the sum of [linear feet] of all orders inlcuded in an offer
    total_feet = pooled.groupby("OFFER_ID")["PALLETIZED_LINEAR_FEET"].transform("sum")

    # calculates the prorated rate
    pooled["PRORATED_RATE_USD"] = pooled["RATE_USD"] * pooled["PALLETIZED_LINEAR_FEET"] / total_feet

    # drops OFFER_ID
    pooled = pooled.drop("OFFER_ID", axis=1)

    return pooled

