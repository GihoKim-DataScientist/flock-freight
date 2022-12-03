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

def join_offers_orders(offers, orders, how="left", on="REFERENCE_NUMBER"):
    """
    Returns a table with each offer paired with its order

    Args:
        offers (DataFrame): offers table
        orders (DataFrame): orders table
    """

    return pd.merge(offers, orders, how=how, on=on)

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
    df = df[df["REMAINIG_TIME"]>0].reset_index(drop=True)

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

def get_business_hours(df, order="ORDER_DATETIME_PST", pickup="PICKUP_DEADLINE_PST"):
    """
    Count number of hours from ORDER_DATETIME_PST to PICKUP_DEADLINE_PST that 
    are in the business hours. Create a new column called BUSINESS_HOURS_ORDER_PICKUP.

    Args:
        df (DataFrame): dataframe to add BUSINESS_HOURS_ORDER_PICKUP
        order (Series): order date and time
        pickup (Series): pickup date and time
        
    It takes about 2 minutes to run.
    """
    import datetime
    # packages to generate the rule of business hours and calculate the hours
    import businesstimedelta
    import holidays as pyholidays
    
    # Set the working hours and days
    work_hours = businesstimedelta.WorkDayRule(start_time=datetime.time(8),
                                               end_time=datetime.time(18),
                                               working_days=[0, 1, 2, 3, 4])

    # Get possible holidays
    all_holidays = pyholidays.UnitedStates()
    holidays = businesstimedelta.HolidayRule(all_holidays)

    # Create the duration of business hours
    business_hours = businesstimedelta.Rules([work_hours, holidays])
    
    def business_hrs(start, end):
        diff_hours = business_hours.difference(start, end)
        return diff_hours.hours + float(diff_hours.seconds) / float(3600)
    
    # Add a new column called BUSINESS_HOURS_ORDER_PICKUP
    df["BUSINESS_HOURS_ORDER_PICKUP"] = df.apply(
        lambda row: business_hrs(row[order], 
                                 row[pickup]), axis=1
    )
    return df

def get_off_business_hours(df, order="ORDER_DATETIME_PST", pickup="PICKUP_DEADLINE_PST"):
    """
    Count number of hours from ORDER_DATETIME_PST to PICKUP_DEADLINE_PST that are not in 
    the business hours. Create a new column called OFF_BUSINESS_HOURS_ORDER_PICKUP.

    Args:
        df (DataFrame): dataframe to add OFF_BUSINESS_HOURS_ORDER_PICKUP
        order (Series): order date and time
        pickup (Series): pickup date and time
        
    It takes about 1 minute to run.
    """
    import datetime
    # packages to generate the rule of business hours and calculate the hours
    import businesstimedelta
    
    # Assume the work rule is from 6PM to 8AM of the next day
    # Weekdays from Monday to Friday
    off_weekday = businesstimedelta.WorkDayRule(start_time=datetime.time(18),
                                                end_time=datetime.time(8),
                                                working_days=[0, 1, 2, 3, 4])

    # Assume the work rule is the entire 24 hours
    # On weekend
    off_weekend = businesstimedelta.WorkDayRule(start_time=datetime.time(0),
                                                end_time=datetime.time(23),
                                                working_days=[5, 6])

    # Don't add holidays. Assume we work on holidays

    # Combine them to an off business hours plan
    off_business_hours = businesstimedelta.Rules([off_weekday, off_weekend])
    
    def off_business_hrs(start, end):
        diff_hours = off_business_hours.difference(start, end)
        return diff_hours.hours + float(diff_hours.seconds) / float(3600)
    
    df["OFF_BUSINESS_HOURS_ORDER_PICKUP"] = df.apply(
        lambda row: off_business_hrs(row[order], 
                                     row[pickup]), axis=1
    )
    return df
    
def get_weekday(df, pickup="PICKUP_DEADLINE_PST"):
    """
    Get the day of the week of each pickup deadline. Create a new column called WEEKDAY_NUM.
    
    Args:
        df (DataFrame): dataframe to add WEEKDAY_NUM
        pickup (Series): pickup date and time
    """
    df["WEEKDAY_NUM"] = df[pickup].apply(lambda time: time.weekday())
    return df                             

def impute_mileage(df, drop=True):
    """
    Args:
        df (DataFrame): DataFrame to impute
        drop (bool, optional): Whether to drop previously unseen origin-destionation pairs. Defaults to True.
    """

    def impute_mileage_apply(df):
        if not np.isnan(df["APPROXIMATE_DRIVING_ROUTE_MILEAGE"]):
            return df["APPROXIMATE_DRIVING_ROUTE_MILEAGE"] 
        if not np.isnan(dists[str(df["ORIGIN_CITY"]) + " " + str(df["DESTINATION_CITY"])]):
            return dists[df["ORIGIN_CITY"] + " " + df["DESTINATION_CITY"]]
        if df["ORIGIN_CITY"] == df["DESTINATION_CITY"]:
            return 10
        else:
            return np.nan

    origin_dest_pair = df["ORIGIN_CITY"] + " " + df["DESTINATION_CITY"]
    mileage = df["APPROXIMATE_DRIVING_ROUTE_MILEAGE"]

    from collections import defaultdict
    dists = defaultdict(lambda : np.nan)
    for pair, dist in zip(origin_dest_pair, mileage):
        if not np.isnan(dist):
            dists[pair] = dist

    df["APPROXIMATE_DRIVING_ROUTE_MILEAGE"] = df.apply(impute_mileage_apply, axis=1)

    if drop:
        df = df[~df.isna()["APPROXIMATE_DRIVING_ROUTE_MILEAGE"]].reset_index(drop=True)

    return df

def popular_cities(df, cols, threshold=0.005):
    """
    Categorizes cities that appear in less than 0.5% of all rows as Others

    Args:
        df (DataFrame): DataFrame to manipulate
        col (list): list of names of the columns to manipulate
        threshold (float, optional): percentage threshold (0<x<1) to define what is "popular". Defaults to 0.05.

    Returns:
        _type_: _description_
    """
    for col in cols:
        popular_cities = df[col] * (df.groupby(col)[col].transform("count") >= len(df) * threshold)
        df[col] = pd.Series(np.where((popular_cities == ""), "Other", popular_cities))

    return df