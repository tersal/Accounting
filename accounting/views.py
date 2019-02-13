from datetime import date, datetime
import json
# You will probably need more methods from flask but this one is a good start.
from flask import render_template, request

# Import things from Flask that we need.
from accounting import app, db

# Import our models
from models import Contact, Invoice, Policy
from utils import PolicyAccounting

# Routing for the server.
@app.route("/")
def index():
    # You will need to serve something up here.
    return render_template('index.html')

# Process data
@app.route("/consult_policy", methods=['POST'])
def consult_data():
    response = {}
    list_invoices = []
    data = request.json
    curr_date = datetime.strptime(data['date'], "%Y-%m-%d")
    policy_id = int(data['policy_id'])
    pa = PolicyAccounting(policy_id)

    # Get current balance to date
    response["total_balance"] = pa.return_account_balance(date_cursor=curr_date)
    # Get invoices
    invoices = Invoice.query.filter_by(policy_id=policy_id) \
                      .filter(Invoice.bill_date <= curr_date ) \
                      .filter(Invoice.deleted == False) \
                      .order_by(Invoice.bill_date) \
                      .all()

    for invoice in invoices:
        dict_invoice = {
            'bill_date': invoice.bill_date.strftime("%m/%d/%Y"),
            'due_date': invoice.due_date.strftime("%m/%d/%Y"),
            'cancel_date': invoice.cancel_date.strftime("%m/%d/%Y"),
            'amount_due': invoice.amount_due
        }
        list_invoices.append(dict_invoice)

    response['invoices'] = list_invoices

    return json.dumps(response)


