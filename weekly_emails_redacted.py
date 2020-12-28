# gets traffic data from google analytics

from apiclient.discovery import build
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
import datetime
import pytz
PATH = "/home/bakichu77/mysite/"

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
  # set start date to 28 days ago
  today = datetime.datetime.now(pytz.timezone("US/Eastern"))
  start_date = (today - datetime.timedelta(days = 28)).replace(tzinfo=pytz.timezone("US/Eastern"))
  start_date_text = start_date.strftime("%Y-%m-%d")

  return analytics.reports().batchGet(
      body={
        'reportRequests': [
        {
          'viewId': VIEW_ID,
          "pageSize": 100000,
          'dateRanges': [{'startDate': start_date_text, 'endDate': 'today'}],
          'metrics': [{'expression': 'ga:totalEvents'}],
          'dimensions': [{'name': 'ga:landingPagePath'}, {"name": "ga:eventAction"},
                        {"name": "ga:pageTitle"}, {"name": "ga:date"}]
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

# link id: (Content Creator, site tag, contact email, payment email, promo code)
LINKS = {"link_id": ("cc_name", "cc_site_tag", "cc_contact_email", "cc_payment_email", "cc_promo_code")}

def match_client_id(client_id):
    return LINKS[client_id]

def format_sales_df(df):
    # format columns for output
    try:
        df["Sale Price"] =  df["Sale Price"].map('${:,.2f}'.format)
        df["Discount"] =    df["Discount"].map('${:,.2f}'.format)
        df["Tax"] =         df["Tax"].map('${:,.2f}'.format)
        df["Shipping"] =    df["Shipping"].map('${:,.2f}'.format)
        df["Customer Paid"] = df["Customer Paid"].map('${:,.2f}'.format)
        df["Credit Card Processing Fee"] = df["Credit Card Processing Fee"].map('${:,.2f}'.format)
        df["Revenue"] =     df["Revenue"].map('${:,.2f}'.format)
        df["Your Cut (%)"] = df["Your Cut (%)"].map('{:,.0%}'.format)
        df["Your Cut ($)"] = df["Your Cut ($)"].map('${:,.2f}'.format)
    except:
        pass
    try:
        # handles revenue vs profit-based clients (basically only Loop)
        df["Revenue After Shipping"] = df["Revenue After Shipping"].map('${:,.2f}'.format)
        df["Cost of Production"] = df["Cost of Production"].map('${:,.2f}'.format)
        df["Profit"] =      df["Profit"].map('${:,.2f}'.format)
    except:
        pass

    return df

def generate_weekly_data(client_id):
    # open get info necessary to find data for each client
    client, client_tag, email, payment_email, promo_code = match_client_id(client_id)
    print(email)

    # first row of content creator excel sheet contains last and next payday,
    # along with current and last payment
    fr = list(pd.read_excel(PATH + "sheets/" + client + ".xlsx", nrows = 0, usecols = [2, 3, 4, 5]))

    # strip "Last Payday:\n" and "Next Payday:\n" from string then convert to date
    last_payday = datetime.datetime.strptime(fr[0][13:], '%Y-%m-%d').date()
    next_payday = datetime.datetime.strptime(fr[1][13:], '%Y-%m-%d').date()

    # print(last_payday)
    # print(next_payday)

    # get traffic stats from first row
    fr_traffic = list(pd.read_excel(PATH + "sheets/" + client + ".xlsx", nrows = 0, usecols = [6, 7, 8]))

    # int(float()) prevents error that sometimes occurs
    users_last_28 = int(float(fr_traffic[0]))
    users_last_7 = int(float(fr_traffic[1]))

    # print(fr)
    # change formatting a little
    current_payment = fr[2].replace("Period", "Payment").replace("\n", " ")
    last_payment = fr[3].strip().replace("\n", " ")

    # read in sales data and format
    df = pd.read_excel(PATH + "sheets/" + client + ".xlsx", skiprows = 2)
    client_df = format_sales_df(df)

    # extract products that were sold this period
    client_df["Order Date"] = pd.to_datetime(client_df["Order Date"]).dt.date

    # reduce dataframe to sales this week
    # UNCOMMENT OUT
    client_df_7 = client_df.loc[(client_df["Order Date"] >= last_payday) & (client_df["Order Date"] < next_payday)]

    # print(client_df_7)
    sales = client_df_7.groupby(["Product Name"]).sum().drop("ID", axis = "columns")
    sales = sales.reset_index()

    # format text about sales, account for potential for no sales
    sales["Sales Text"] = sales["Product Name"] + " (" + sales["Quantity"].astype(str) + ")"
    email_sales_text = ", ".join(list(sales["Sales Text"]))
    if email_sales_text == "":
        email_sales_text = "No sales this week"
    else:
        email_sales_text = "Sales this week: " + email_sales_text


    # find product views last 28 days (event data is limited to last 28 days)
    event_df = pd.read_csv(PATH + "weeklyemails/event_data.csv")
    # print(event_df)

    all_product_views = event_df[event_df["Event Action"] == "Viewed Product"]
    # print(all_product_views)

    # find sum of all product views
    product_view_sums = all_product_views.groupby("Page Title").sum()

    # restrict to only product views of this content creator, sort descending
    cc_view_sums = product_view_sums[product_view_sums.index.str.contains(client)]["Total Events"].sort_values(ascending = False)

    # get top 5 products of last month (or fewer if that many haven't been viewed)
    # format string appropriately
    top_5 = ", ".join(list(cc_view_sums.iloc[0:6].index)).replace(" – Modern Media Merch", "")
    top_5 = top_5.replace(client + " ", "")
    if top_5 != "":
        top_5 = "Most viewed products (last 28 days): " + top_5


    # data seems unreliable, drop for now
    '''
    # find add to carts last 28 and 7 days for this content creator
    all_add_to_carts = event_df[event_df["Event Action"] == "Started Order"]

    cc_all_add_to_carts = all_add_to_carts[all_add_to_carts["Landing Page"].str.contains(client_tag)]

    print(all_add_to_carts)
    print(cc_all_add_to_carts)
    '''

    # generate link to dashboard
    link = "momeme.design/" + client_id

    start_day = last_payday.strftime("%B %d")
    end_day = (next_payday - datetime.timedelta(days = 1)).strftime("%B %d")
    date_str = start_day + " - " + end_day
    print(date_str)

    return(email, client, date_str, link, current_payment, last_payment,
            email_sales_text, top_5, users_last_28, users_last_7, next_payday,
            payment_email, promo_code)

import os
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from sendgrid.helpers.mail import *
import time


def send_emails(email_df):
    today = datetime.datetime.now(pytz.timezone("US/Eastern"))
    today_str = today.strftime("%Y-%m-%d")
    print(today)

    # client : {"payment": payment_amt}
    # TODO: add payment email, promo code
    payment_dict = {}
    total_payment = 0

    print(email_df)
    for index, row in email_df.iterrows():
        # check if today is send date
        if str(row["Next Payday"]) == today_str:
            print(row)
            print("Send Date")

            send_day = today

            # determine send times to me and content creator
            ny_tz = pytz.timezone('America/New_York')
            to_me = int(ny_tz.localize(datetime.datetime(send_day.year, send_day.month, send_day.day, 6, 30, 0, 0)).timestamp())
            to_cc = int(ny_tz.localize(datetime.datetime(send_day.year, send_day.month, send_day.day, 15, 30, 0, 0)).timestamp())

            print(to_me)
            print(to_cc)
        else:
            # if not the right day, write to log and break
            print("Not Send Date")
            to_me = 0
            continue
        mail = Mail()
        mail.from_email = Email('bassel@modernmediamerch.com', 'Bassel from Modern Media Merch')
        mail.template_id = 'd-a5ba3dbe5dac4c67ad430a87bb92287a'
        p = Personalization()

        template_data = {
            "client_name" : row["Client"],
            'date_text': row["Date Text"],
            'dashboard_link': row["Dashboard"],
            'promo_code': row["Promo Code"],
            'current_payment': row["Current Payment"],
            'last_payment': row["Last Payment"],
            'sales_text': row["Sales Text"],
            'top_5_products': row["Most Popular Products"],
            'users_28' : row["Users last 28"],
            "users_7" : row["Users last 7"]
        }
        p.dynamic_template_data = template_data

        # schedule email to me
        p.add_to(Email('bassel@modernmediamerch.com'))
        mail.add_personalization(p)
        mail.send_at = to_me

        sg = SendGridAPIClient('redacted')


        response = sg.client.mail.send.post(request_body=mail.get())
        print(response.status_code)
        print(response.headers)
        print(response.body)

        time.sleep(30)


        # schedule email to content creator
        p2 = Personalization()
        p2.dynamic_template_data = template_data
        p2.add_to(Email(row["Email"]))

        mail2 = Mail()
        mail2.from_email = Email('bassel@modernmediamerch.com', 'Bassel from Modern Media Merch')
        mail2.template_id = 'redacted'
        mail2.add_personalization(p2)
        mail2.send_at = to_cc


        response = sg.client.mail.send.post(request_body=mail2.get())
        print(response.status_code)
        print(response.headers)
        print(response.body)


        client = row["Client"]
        payment_dict[client] = {}

        payment_dict[client]["Payment"] = "$" + str(row["Current Payment"][18:])
        payment_dict[client]["Payment Email"] = row["Payment Email"]
        total_payment += float(str(row["Current Payment"][18:]))

    # send summary payment email to me (only if it is a send date)
    if to_me != 0:
        mail = Mail()
        mail.from_email = Email('bassel@modernmediamerch.com', 'Bassel from Modern Media Merch')
        mail.subject = "MMM Payment Summary"

        # create text of summary email
        sum_text = "Total payment: $" + str(total_payment) + "\n\n"
        for client, payments in payment_dict.items():
            sum_text = sum_text + str(client) + ": " + str(payments["Payment"]) + "\n \
                        \tPayment info: " + str(payments["Payment Email"]) + "\n\n"

        print(sum_text)
        mail.content = Content("text/plain", sum_text)
        p = Personalization()
        p.add_to(Email("bassel@modernmediamerch.com"))
        mail.add_personalization(p)


        response = sg.client.mail.send.post(request_body=mail.get())
        print(response.status_code)
        print(response.headers)
        print(response.body)




def main():

    analytics = initialize_analyticsreporting()
    # service sometimes unavailable, attempt to account for this by retrying
    try:
        response = get_report(analytics)
    except:
        response = get_report(analytics)

    # update event data
    df = parse_response(response)
    oldcols = df.columns
    newcols = ["Landing Page", "Event Action", "Page Title", "Date", "Total Events"]
    df = df.rename(dict(zip(oldcols, newcols)), axis = "columns")
    df.to_csv(PATH + "weeklyemails/event_data.csv")

    # generate weekly email data for all clients
    cols = ["Email", "Client", "Date Text", "Dashboard", "Current Payment",
            "Last Payment", "Sales Text", "Most Popular Products",
            "Users last 28", "Users last 7", "Next Payday", "Payment Email", "Promo Code"]
    df2 = pd.DataFrame(columns = cols)
    for cc_id in LINKS.keys():
        df2.loc[len(df2)] = (list(generate_weekly_data(cc_id)))
    print(df2)
    df2.to_csv(PATH + "weeklyemails/email_data.csv", index = False)

    send_emails(df2)

    # force error
    #print(asnsd[2312])


main()







