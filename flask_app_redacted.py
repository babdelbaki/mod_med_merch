from flask import Flask, render_template
import pandas
import os


app = Flask(__name__)
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0
PATH = "redacted"

# link id: (Content Creator, site tag)
LINKS = {"link_id": ("cc_name", "cc_site_tag"),}

def match_client_id(client_id):
    return LINKS[client_id]

@app.route("/MASTER_LINK")
def master():
     with app.app_context():
        return render_template("links.html", link_list=LINKS)


@app.route('/<client_id>')
def images(client_id):
    pics = os.listdir(PATH + 'static/')

    client, client_tag = match_client_id(client_id)

    # get traffic stats and graphs
    fr_traffic = pandas.read_excel(PATH + "sheets/" + client + ".xlsx", nrows = 0, usecols = [6, 7, 8])
    fr_stats = list(fr_traffic.columns)

    # empty dictionary {Fig Caption: [pic link, number of users]}
    cc_pics = {"Last 28 Days" : [0, 0], "Last 7 Days": [0, 0], "Last 24 Hours": [0,0]}
    for pic in pics:
        if client_tag in pic:
            # fix order of pictures
            # associate pic link/sum of users to each caption
            # int/float because sum sometimes is returned as float (?)
            if "28d" in pic:
                cc_pics["Last 28 Days"][0] = pic
                cc_pics["Last 28 Days"][1] = int(float(fr_stats[0]))
            if "7d" in pic:
                cc_pics["Last 7 Days"][0] = pic
                cc_pics["Last 7 Days"][1] = int(float(fr_stats[1]))
            if "24h" in pic:
                cc_pics["Last 24 Hours"][0] = pic
                cc_pics["Last 24 Hours"][1] = int(float(fr_stats[2]))




    df = pandas.read_excel(PATH + "sheets/" + client + ".xlsx", skiprows = 2)

    # fr contains next and last payday, next and last payment
    fr = pandas.read_excel(PATH + "sheets/" + client + ".xlsx", nrows = 0, usecols = 5)

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

    with app.app_context():
        return render_template("simple.html", pics=cc_pics, headers = list(fr)) + df.to_html(index = False)


# No caching at all for API endpoints.
@app.after_request
def add_header(response):
    # response.cache_control.no_store = True
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '-1'
    return response