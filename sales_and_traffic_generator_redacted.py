#!/usr/bin/env python3.8
# coding: utf-8


import requests
import pandas as pd
from datetime import date
import datetime

PATH = "/home"

API_KEY = "redacted"
password = "redacted"
host_name = "redacted"
version = "/admin/api/2020-04/"
orders_wanted = "orders.json?status=any"

api_call = "https://" + API_KEY + password + host_name + version + orders_wanted

# specific client names and profit-sharing agreements have been removed,
# {client_name: [type_of_split, percent_split, payment_frequency, start_date, website_tag]}
clients = {"redacted1": ["R", 0.3, "W", datetime.datetime(2020, 5, 25), "redacted1"],
           "redacted2": ["P", 0.5, "W", datetime.datetime(2020, 7, 6), "redacted2"],}



r = requests.get(api_call)

order_data = r.json()



PAY_TYPE = 0
PAY_CUT = 1
PAY_SCHEDULE = 2
START_DATE = 3
CLIENT_TAG = 4

def check_cost(variant, product_name):
    if "Tee" in product_name:
        if variant == "S":
            return 6.09
        elif variant == "M":
            return 6.21
        elif variant == "L":
            return 6.47
        elif variant == "XL":
            return 6.71
        elif variant == "2XL":
            return 6.95
        elif variant == "3XL":
            return 7.15
        elif variant == "4XL":
            return 7.35
        elif variant == "5XL":
            return 7.55
    elif "Hoodie" in product_name:
        if variant == "S":
            return 19.34
        elif variant == "M":
            return 19.72
        elif variant == "L":
            return 20.18
        elif variant == "XL":
            return 20.46
        elif variant == "2XL":
            return 20.75
        elif variant == "3XL":
            return 20.96
        elif variant == "4XL":
            return 21.07
        elif variant == "5XL":
            return 21.21

client_dfs = {}

for client, client_data in clients.items():
    df = pd.DataFrame(columns = ["ID", "Order Date", "Product Name", "Variant", "Quantity", "Sale Price", "Discount", "Tax",
                            "Shipping", "Customer Paid", "Credit Card Processing Fee"])

    for order in order_data["orders"]:
        num_items = 0

        for item in order["line_items"]:
            if client not in item["title"]:
                belongs = False
                continue
            else: belongs = True

            id = order["id"]
            order_date = order["created_at"][:10]
            title = item["title"]
            # account for color in variant
            variant = item["variant_title"].split("/")[-1].strip()
            sale_price = float(item["price"])
            qty = item["quantity"]
            num_items +=1

            list_item = item["discount_allocations"]
            if list_item:
                discount = float(list_item[0]["amount"])
            else: discount = 0


            df = df.append({"ID":id, "Order Date":order_date, "Product Name": title, "Variant": variant, "Quantity":qty,
                            "Sale Price":sale_price, "Discount":discount}, ignore_index = True)

            # if order belongs to this client
            if belongs:
                if order["tax_lines"]:
                    tax = order["tax_lines"][0]["price"]
                else: tax = 0
                item_tax = round(float(tax) / num_items, 2)

                # order_shipping = order["shipping_lines"][0]["price"]

                # item_shipping = round(float(order_shipping) / num_items, 2)
                # calculate shipping costs (monster digital)
                country = order["shipping_address"]["country_code"]
                if country == "US" and num_items == 1:
                    item_shipping = 4
                    cust_paid = 4
                elif country == "US" and num_items > 1:
                    item_shipping = 2 + (num_items - 1)
                    cust_paid = 0
                elif num_items == 1:
                    item_shipping = 8
                    cust_paid = 8
                elif num_items >1:
                    item_shipping = 4 + (num_items - 1) * 2
                    cust_paid = 0

                item_tot = float(order["total_price"]) / num_items
                cc_fee = round(item_tot * 0.029 + 0.3, 2)
                # calculate shipping per item, credit card fee, revenue/profit
                # artist cut
                # then move to for loop above and append to df

                cust_paid = round(float(sale_price) + cust_paid + item_tax - float(discount), 2)

                if client_data[PAY_TYPE] == "R":
                    # for revenue based clients
                    revenue = cust_paid - cc_fee
                    df.loc[df["ID"] == id, "Revenue"] = revenue
                    df.loc[df["ID"] == id, "Your Cut (%)"] = client_data[PAY_CUT]
                    df.loc[df["ID"] == id, "Your Cut ($)"] = round(client_data[PAY_CUT] * revenue, 2)
                elif client_data[PAY_TYPE] == "P":
                    # for profit based clients
                    revenue = cust_paid - cc_fee
                    revenue_shipping = revenue - item_shipping
                    df.loc[df["ID"] == id, "Revenue"] = revenue
                    df.loc[df["ID"] == id, "Revenue After Shipping"] = revenue_shipping
                    df["Cost of Production"] = df.apply(lambda x: check_cost(x["Variant"], x["Product Name"]), axis = 1) #["Variant"].apply(check_cost)
                    df["Profit"] = df["Revenue After Shipping"] - df["Cost of Production"]
                    df["Your Cut (%)"] = client_data[PAY_CUT]
                    profits = pd.to_numeric(df["Profit"])
                    df["Your Cut ($)"] = profits * client_data[PAY_CUT]



                df.loc[df["ID"] == id, ["Tax", "Shipping", "Customer Paid", "Credit Card Processing Fee"]
                      ] = (item_tax, item_shipping, cust_paid, cc_fee)

    client_dfs[client] = {}
    client_dfs[client]["df"] = df
    client_dfs[client]["paytype"] = client_data[PAY_TYPE]
    client_dfs[client]["paydate"] = client_data[START_DATE]
    client_dfs[client]["client_tag"] = client_data[CLIENT_TAG]
    print(df)

# add sample sale for demonstration and to ensure dashboard displays properly
add_sample("redacted1")
add_sample("redacted2")


# gets traffic data from google analytics

from apiclient.discovery import build
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
import datetime
import pytz

SCOPES = ['https://www.googleapis.com/auth/analytics.readonly']
KEY_FILE_LOCATION = "redacted.json"
VIEW_ID = "redacted"

def initialize_analyticsreporting():
  """Initializes an Analytics Reporting API V4 service object.

  Returns:
    An authorized Analytics Reporting API V4 service object.
  """
  credentials = ServiceAccountCredentials.from_json_keyfile_name(
      KEY_FILE_LOCATION, SCOPES)

  # Build the service object.
  analytics = build('analyticsreporting', 'v4', credentials=credentials)

  return analytics

def get_report(analytics):
  """Queries the Analytics Reporting API V4.

  Args:
    analytics: An authorized Analytics Reporting API V4 service object.
  Returns:
    The Analytics Reporting API V4 response.
  """
  # set start date to 4 weeks ago
  today = datetime.datetime.now(pytz.timezone("US/Eastern"))
  four_weeks_ago = (today - datetime.timedelta(days = 28)).replace(tzinfo=pytz.timezone("US/Eastern"))
  fwa_text = four_weeks_ago.strftime("%Y-%m-%d")

  return analytics.reports().batchGet(
      body={
        'reportRequests': [
        {
          'viewId': VIEW_ID,
          "pageSize": 100000,
          'dateRanges': [{'startDate': fwa_text, 'endDate': 'today'}],
          'metrics': [{'expression': 'ga:sessions'}, {"expression": "ga:users"}, {"expression": "ga:pageviews"}],
          'dimensions': [{'name': 'ga:landingPagePath'}, {"name": "ga:dateHourMinute"}, {"name": "ga:date"}, {"name": "ga:hour"}]
        }]
      }
  ).execute()


def parse_response(response):
  """Parses and converts the Analytics Reporting API V4 response to pandas dataframe

  Args:
    response: An Analytics Reporting API V4 response.
  Returns:
    Pandas dataframe with analytics data
  """

  for report in response.get('reports', []):
    columnHeader = report.get('columnHeader', {})
    dimensionHeaders = columnHeader.get('dimensions', [])
    metricHeaders = columnHeader.get('metricHeader', {}).get('metricHeaderEntries', [])

    cols = dimensionHeaders.append(metricHeaders)
    df = pd.DataFrame(columns = cols)

    for i, row in enumerate(report.get('data', {}).get('rows', [])):
      dimensions = row.get('dimensions', [])
      dateRangeValues = row.get('metrics', [])

      for header, dimension in zip(dimensionHeaders, dimensions):
          df.loc[i, header] = dimension

      for j, values in enumerate(dateRangeValues):
        for metricHeader, value in zip(metricHeaders, values.get('values')):
          df.loc[i, metricHeader.get("name")] = value
  return df


def get_timeperiod(hour):
    # returns which quarter of day a given hour is in
    #if hour
    if hour >= 0 and hour < 6:
        return "00"
    elif hour >= 6 and hour < 12:
        return "06"
    elif hour >= 12 and hour < 18:
        return "12"
    elif hour >= 18 and hour < 24:
        return "18"
    pass

def main():
    analytics = initialize_analyticsreporting()
    # service sometimes unavailable, attempt to account for this by retrying
    try:
        response = get_report(analytics)
    except:
        response = get_report(analytics)
    df = parse_response(response)
    oldcols = df.columns
    newcols = ["Landing Page", "YMDHM", "Date", "Hour", "Sessions", "Users", "Pageviews"]
    df = df.rename(dict(zip(oldcols, newcols)), axis = "columns")
    df.to_csv(PATH + "traffic_data.csv")
main()

# function for creating traffic plots from google analytics
import matplotlib.pyplot as plt
import seaborn as sns
import os

def create_images(content_creator):
    df = pd.read_csv(PATH + "traffic_data.csv")
    cc_df = df[df["Landing Page"].str.contains(content_creator)]
    cc_df["Date"] = pd.to_datetime(cc_df["YMDHM"], format = "%Y%m%d%H%M").dt.tz_localize(tz = "US/Eastern")

    # delete all images that contain the content creator's name (cache busting)
    pics = os.listdir(PATH + 'static/')
    for pic in pics:
        if content_creator in pic:
            os.remove(PATH + "static/" + pic)

    # then add timestamp to image names
    timestmp = datetime.datetime.now(pytz.timezone("US/Eastern")).strftime("%Y%m%d%H%M")

    # all time (deprecated for now)
    '''
    cc_at = cc_df.groupby("Date").agg("sum")
    cc_at_users = pd.DataFrame(cc_at.resample("1D")["Users"].sum())
    cc_at_users["Date"] = cc_at_users.index.strftime("%Y-%m-%d")

    plt.figure(figsize = (10,6))
    bar = sns.barplot(data = cc_at_users, x = "Date", y = "Users", color = "Blue", ci = None)
    bar.set_xticklabels(bar.get_xticklabels(), rotation = 45, horizontalalignment = "right", fontsize = "small")
    plt.tight_layout()
    bar.figure.savefig("static/" + content_creator + "alltime" + ".png")
    plt.close()
    '''

    # last 28 days
    today = datetime.datetime.now(pytz.timezone("US/Eastern"))
    four_weeks_ago = (today - datetime.timedelta(days = 28)).replace(tzinfo=pytz.timezone("US/Eastern"))

    cc_28 = cc_df[cc_df["Date"] > four_weeks_ago]
    cc_28["DT_YMDHM"] = pd.to_datetime(cc_28["YMDHM"], format = "%Y%m%d%H%M", errors = "coerce").dt.tz_localize("US/Eastern")

    # add blank rows so time continues from 4 weeks ago to now
    inter_df = pd.DataFrame(columns = cc_28.columns)
    inter_df.loc[0, "DT_YMDHM"] = today
    inter_df.loc[0, "Users"] = 0
    inter_df.loc[1, "DT_YMDHM"] = four_weeks_ago
    inter_df.loc[1, "Users"] = 0
    cc_28 = cc_28.append(inter_df)

    # resample to fill in days with no users
    cc_28_users = pd.DataFrame(cc_28.set_index("DT_YMDHM").resample("1D")["Users"].sum())
    cc_28_users["Day"] = cc_28_users.index.date.astype("datetime64").astype("str")

    # calculate sum of users
    sum_28 = cc_28_users["Users"].sum()

    # plot and format
    plt.figure(figsize = (10,6))
    bar = sns.barplot(data = cc_28_users, x = "Day", y = "Users", color = "Blue", ci = None)
    bar.set_xticklabels(bar.get_xticklabels(), rotation = 45, horizontalalignment = "right", fontsize = "small")
    bar.set(ylim = (0, None))
    plt.tight_layout()
    bar.figure.savefig(PATH + "static/" + content_creator + "28d" + timestmp + ".png")
    plt.close()


    # last 7 days (4 periods per day)
    one_week_ago = (today - datetime.timedelta(days = 7)).replace(tzinfo=pytz.timezone("US/Eastern"))

    cc_7 = cc_df[cc_df["Date"] > one_week_ago]

    # add blank rows so time always displays entire week
    inter_df = pd.DataFrame(columns = cc_7.columns)
    inter_df.loc[0, "YMDHM"] = today.strftime("%Y%m%d%H%M")
    inter_df.loc[0, "Users"] = 0
    inter_df.loc[1, "YMDHM"] = one_week_ago.strftime("%Y%m%d%H%M")
    inter_df.loc[1, "Users"] = 0
    cc_7 = cc_7.append(inter_df)

    # sum users by time period, reorganize df for plotting
    # resample to fill in hours with no users
    cc_7["DT_YMDHM"] = pd.to_datetime(cc_7["YMDHM"], format = "%Y%m%d%H%M", errors = "coerce").dt.tz_localize("US/Eastern")
    cc_7_users = pd.DataFrame(cc_7.set_index("DT_YMDHM").resample("1H").sum())
    cc_7_users["Hour"] = cc_7_users.index.hour
    cc_7_users["Hour"] = cc_7_users["Hour"].apply(get_timeperiod)
    cc_7_users["Day"] = cc_7_users.index.date.astype("datetime64").astype("str")
    cc_7_users["Datetime"] = cc_7_users["Day"] + ":" + cc_7_users["Hour"].astype("str")
    cc_7_users = cc_7_users.groupby("Datetime").agg("sum")
    cc_7_users["Datetime"] = cc_7_users.index

    # calculate sum of users
    sum_7 = cc_7_users["Users"].sum()

    # plot
    plt.figure(figsize = (10,6))
    bar = sns.barplot(data = cc_7_users, x = "Datetime", y = "Users", color = "Blue", ci = None)
    bar.set_xticklabels(bar.get_xticklabels(), rotation = 45, horizontalalignment = "right", fontsize = "small")
    bar.set(ylim = (0, None))
    plt.tight_layout()
    bar.figure.savefig(PATH + "/static/" + content_creator + "7days" + timestmp + ".png")
    plt.close()

    # last 24 hours
    yesterday = (today - datetime.timedelta(days = 1)).replace(tzinfo=pytz.timezone("US/Eastern"))
    cc_24 = cc_df[cc_df["Date"] > yesterday]
    cc_24["DT_YMDHM"] = pd.to_datetime(cc_24["YMDHM"], format = "%Y%m%d%H%M", errors = "coerce").dt.tz_localize("US/Eastern")

    # add blank rows so time continues from yesterday to now
    inter_df = pd.DataFrame(columns = cc_24.columns)
    inter_df.loc[0, "DT_YMDHM"] = today
    inter_df.loc[0, "Users"] = 0
    inter_df.loc[1, "DT_YMDHM"] = yesterday
    inter_df.loc[1, "Users"] = 0
    cc_24 = cc_24.append(inter_df)

    # resample to fill in hours with no users
    cc_24_users = pd.DataFrame(cc_24.set_index("DT_YMDHM").resample("1H")["Users"].sum())
    cc_24_users["Hour"] = cc_24_users.index.hour
    cc_24_users["Day"] = cc_24_users.index.date.astype("datetime64").astype("str")
    cc_24_users["Datetime"] = cc_24_users["Day"] + ":" + cc_24_users["Hour"].astype("str")

    # calculate sum of users
    sum_24 = cc_24_users["Users"].sum()

    # plot
    plt.figure(figsize = (10,6))
    bar = sns.barplot(data = cc_24_users, x = "Datetime", y = "Users", color = "Blue", ci = None)
    bar.set_xticklabels(bar.get_xticklabels(), rotation = 45, horizontalalignment = "right", fontsize = "small")
    bar.set(ylim = (0, None))
    plt.tight_layout()
    bar.figure.savefig(PATH + "static/" + content_creator + "24hrs" + timestmp + ".png")
    plt.close()

    return (sum_28, sum_7, sum_24)

for client, client_sales in client_dfs.items():
    # handles if there's no traffic yet
    (sum_28, sum_7, sum_24) = (0, 0, 0)
    try:
        (sum_28, sum_7, sum_24) = create_images(client_sales["client_tag"])
    except:
       pass

    client_df = client_sales["df"]
    paytype = client_sales["paytype"]

    print(client)
    spr = pd.ExcelWriter(PATH + "sheets/" + client + ".xlsx", engine='xlsxwriter')

    date_str = "Last Updated at:\n" + datetime.datetime.now(pytz.timezone("US/Eastern")).strftime("%Y-%m-%d %H:%M")

    # append data after client row
    client_df.to_excel(spr, startrow = 2, sheet_name = "Sheet1", index = False)

    workbook  = spr.book
    worksheet = spr.sheets["Sheet1"]

    format_wrap = workbook.add_format({"text_wrap" : True})

    # client and last updated date
    worksheet.write("A1", client, format_wrap)
    worksheet.write("B1", date_str, format_wrap)


    # calculate last and next payday using weekday of start date
    today = date.today()
    payday = client_sales["paydate"].weekday()

    last_payday = today - datetime.timedelta(days=today.weekday())
    next_payday = today + datetime.timedelta(days=-today.weekday(), weeks=1)

    # handle if today is a payday
    if today.weekday() == payday:
        last_payday = today - datetime.timedelta(weeks = 1)
        next_payday = today

    payday_before = last_payday - datetime.timedelta(days = 7)

    last_payday_str = "Last Payday:\n" + last_payday.strftime("%Y-%m-%d")
    worksheet.write("C1", last_payday_str, format_wrap)
    next_payday_str = "Next Payday:\n" + next_payday.strftime("%Y-%m-%d")
    worksheet.write("D1", next_payday_str, format_wrap)

    # calculate last and next payment
    client_df["Order Date"] = pd.to_datetime(client_df["Order Date"]).dt.date

    try:
        # handles if there have been no sales yet
        current_period = client_df.loc[(client_df["Order Date"] >= last_payday) & (client_df["Order Date"] < next_payday), "Your Cut ($)"].sum()
        last_period = client_df.loc[(client_df["Order Date"] >= payday_before) & (client_df["Order Date"] < last_payday), "Your Cut ($)"].sum()

        current_pay_str = "${:,.2f}".format(current_period)
        last_pay_str = "${:,.2f}".format(last_period)

        current_period_str = "Current Period:\n" + current_pay_str
        last_period_str = "Last Payment:\n" + last_pay_str

        worksheet.write("E1", current_period_str, format_wrap)
        worksheet.write("F1", last_period_str, format_wrap)
    except:
        pass

    try:
        # handles if there's no traffic yet
        worksheet.write("G1", sum_28)
        worksheet.write("H1", sum_7)
        worksheet.write("I1", sum_24)
    except:
        pass

    # formatting
    format_curr = workbook.add_format({'num_format': '$#.00'})
    format_pct = workbook.add_format({"num_format": "#%"})

    worksheet.set_column("B:D", 15, format_wrap)

    if paytype == "R":
        worksheet.set_column("F:L", 15, format_curr)
        worksheet.set_column("M:M", 15, format_pct)
        worksheet.set_column("N:N", 15, format_curr)
    elif paytype == "P":
        worksheet.set_column("F:O", 15, format_curr)
        worksheet.set_column("P:P", 15, format_pct)
        worksheet.set_column("Q:Q", 15, format_curr)


    spr.save()





