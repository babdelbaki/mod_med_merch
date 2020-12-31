#!/usr/bin/env python
# coding: utf-8

# to-do: handle paydays that aren't mondays
# re-add TGF
# figure out better way of handling write requests to avoid cap
# transition to csvs on pythonanywhere instead of google sheets
# perhaps google analytics api for traffic?

# In[180]:


import requests
import pandas as pd
import datetime
from datetime import date


# In[181]:


API_KEY = "redacted"
password = "redacted"
host_name = "redacted"
version = "/admin/api/2020-04/"
orders_wanted = "orders.json?status=any"

api_call = "https://" + API_KEY + password + host_name + version + orders_wanted

# client name, type of split (revenue or profit), commission proportion, payment frequency, start date, website tag
clients = {"redacted": ["R", 0.3, "W", datetime.datetime(2020, 05, 25), "redacted1"],
            "redacted2": ["P", 0.5, "W", datetime.datetime(2020, 07, 06), "redacted2"],
           #"TeamGetFight": ["P", 0.5, "W", datetime.datetime(2020, 07, 17), "teamgetfight"],
           "Rust Academy": ["P", 0.5, "W", datetime.datetime(2020, 07, 06), "rust-academy"]}


# In[182]:


r = requests.get(api_call)


# In[183]:


# In[184]:


order_data = r.json()


# In[185]:


# In[186]:


PAY_TYPE = 0
PAY_CUT = 1
PAY_SCHEDULE = 2
START_DATE = 3

def check_cost(variant):
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

                #order_shipping = order["shipping_lines"][0]["price"]

                #item_shipping = round(float(order_shipping) / num_items, 2)
                # calculate shipping costs (monster digital)
                country = order["shipping_address"]["country_code"]
                if country == "US" and num_items == 1:
                    item_shipping = 4
                    cust_paid = 4
                elif country == "US" and num_items >1:
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
                    df["Cost of Production"] = df["Variant"].apply(check_cost)
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
    print(df)


# In[ ]:





# In[187]:


# sample sales

# loop
new_line_1 = pd.DataFrame({"ID":2193556814345, "Order Date": "2020-06-21", "Product Name": "Loop Banner Tee",
                                 "Variant": "L", "Quantity": 1, "Sale Price":21, "Discount":discount, "Tax":0,
                                "Shipping": 4.0, "Customer Paid": 25.0, "Credit Card Processing Fee": 1.03, "Revenue": 23.97,
                                "Your Cut (%)": 0.3, "Your Cut ($)": 7.19}, index = [0])
new_line_2 = pd.DataFrame({"ID":2190542512816, "Order Date": "2020-06-18", "Product Name": "Loop Logo Tee",
                                 "Variant": "S", "Quantity": 1, "Sale Price":21, "Discount":discount, "Tax":0,
                                "Shipping": 4.0, "Customer Paid": 25.0, "Credit Card Processing Fee": 1.03, "Revenue": 23.97,
                                "Your Cut (%)": 0.3, "Your Cut ($)": 7.19}, index = [0])
new_lines = pd.concat([new_line_1, new_line_2]).reset_index(drop = True)
client_dfs["Loop"]["df"] = pd.concat([new_lines, client_dfs["Loop"]["df"]], sort = False).reset_index(drop = True)
client_dfs["Loop"]["df"]["Order Date"] = pd.to_datetime(client_dfs["Loop"]["df"]["Order Date"])
# ensure rows in right order
client_dfs["Loop"]["df"].sort_values(by = ["Order Date"], inplace = True, ascending = False)
client_dfs["Loop"]["df"]["Order Date"] = client_dfs["Loop"]["df"]["Order Date"].apply(str).str.slice(0,10)
# ensure columns in right order
client_dfs["Loop"]["df"] = client_dfs["Loop"]["df"][["ID", "Order Date", "Product Name", "Variant", "Quantity", "Sale Price", "Discount", "Tax",
                            "Shipping", "Customer Paid", "Credit Card Processing Fee", "Revenue", "Your Cut (%)", "Your Cut ($)"]]
#print(client_dfs["Loop"]["df"])

# tz
new_line_1 = pd.DataFrame({"ID":2103668572230, "Order Date": "2020-06-26", "Product Name": "GAMINGwithTZ Logo Tee - BLK",
                                 "Variant": "L", "Quantity": 1, "Sale Price":21, "Discount":discount, "Tax":0,
                                "Shipping": 4.0, "Customer Paid": 25.0, "Credit Card Processing Fee": 1.03, "Revenue": 23.97,
                                "Revenue After Shipping": 19.97, "Cost of Production": 6.47, "Profit":13.51,
                                "Your Cut (%)": 0.5, "Your Cut ($)": 6.75}, index = [0])
client_dfs["GAMINGwithTZ"]["df"] = pd.concat([new_line_1, client_dfs["GAMINGwithTZ"]["df"]], sort = False).reset_index(drop = True)
client_dfs["GAMINGwithTZ"]["df"]["Order Date"] = pd.to_datetime(client_dfs["GAMINGwithTZ"]["df"]["Order Date"])
# ensure rows in right order
client_dfs["GAMINGwithTZ"]["df"].sort_values(by = ["Order Date"], inplace = True, ascending = False)
client_dfs["GAMINGwithTZ"]["df"]["Order Date"] = client_dfs["GAMINGwithTZ"]["df"]["Order Date"].apply(str).str.slice(0,10)
# ensure columns in right order
client_dfs["GAMINGwithTZ"]["df"] = client_dfs["GAMINGwithTZ"]["df"][["ID", "Order Date", "Product Name", "Variant", "Quantity", "Sale Price", "Discount", "Tax",
                            "Shipping", "Customer Paid", "Credit Card Processing Fee", "Revenue", "Revenue After Shipping", "Cost of Production",
                            "Profit", "Your Cut (%)", "Your Cut ($)"]]
#print(client_dfs["GAMINGwithTZ"]["df"])


# In[189]:


import gspread

gc = gspread.service_account(filename='modern-media-merch-792c930e5aad.json')
for client, client_sales in client_dfs.items():
    client_df = client_sales["df"]
    paytype = client_sales["paytype"]

    print(client)
    spr = gc.open(client)
    spr.values_clear("Sheet1!A1:BA10000")
    sh1 = spr.sheet1

    sh1.update([client_df.columns.values.tolist()] + client_df.values.tolist())

    # insert rows at top for aesthetics
    sh1.insert_row([" "])

    # update date
    batch = []
    batch.append(client)
    #sh1.update("A1", client)
    date_str = "Last Updated on: " + date.today().strftime("%Y-%m-%d")
    batch.append(date_str)
    #sh1.update("B1", date_str)

    # calculate last and next payday using weekday of start date
    payday = client_sales["paydate"].weekday()
    today = date.today()
    last_payday = today - datetime.timedelta(days=today.weekday())
    next_payday = today + datetime.timedelta(days=-today.weekday(), weeks=1)
    payday_before = last_payday - datetime.timedelta(days = 7)

    last_payday_str = "Last Payday: " + last_payday.strftime("%Y-%m-%d")
    #sh1.update("C1", last_payday_str)
    batch.append(last_payday_str)
    next_payday_str = "Next Payday: " + next_payday.strftime("%Y-%m-%d")
    #sh1.update("D1", next_payday_str)
    batch.append(next_payday_str)

    # update batch of cells at once
    cell_list = sh1.range("A1:D1")
    for i, val in enumerate(batch):
        cell_list[i].value = val
    sh1.update_cells(cell_list)

    client_df["Order Date"] = pd.to_datetime(client_df["Order Date"])
    try:
        # handles if there have been no sales yet
        current_period = client_df.loc[(client_df["Order Date"] >= last_payday) & (client_df["Order Date"] < next_payday), "Your Cut ($)"].sum()
        print(current_period)
        last_period = client_df.loc[(client_df["Order Date"] >= payday_before) & (client_df["Order Date"] < last_payday), "Your Cut ($)"].sum()
        print(last_period)

        current_period_str = "Current Period: $" + str(round(current_period, 2))
        last_period_str = "Last Payment: $" + str(round(last_period, 2))
        cell_list = sh1.range("E1:F1")
        cell_vals = [current_period_str, last_period_str]
        print(current_period_str)
        print(last_period_str)
        for i, val in enumerate(cell_vals):
            cell_list[i].value = val
        sh1.update_cells(cell_list)
    except:
        pass
    # formatting
    format_wrap = {"wrapStrategy": "WRAP"}
    format_curr = {"numberFormat": {"type":"CURRENCY"}}
    format_pct =  {"numberFormat": {"type":"PERCENT"}}

    sh1.format("A1:F1", format_wrap)
    # different columns for profit vs revenue
    if paytype == "R":
        sh1.format("F:L", format_curr)
        sh1.format("M", format_pct)
        sh1.format("N", format_curr)
    elif paytype == "P":
        sh1.format("F:O", format_curr)
        sh1.format("P", format_pct)
        sh1.format("Q", format_curr)











