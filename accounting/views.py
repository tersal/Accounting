from datetime import date, datetime
import json
# You will probably need more methods from flask but this one is a good start.
from flask import render_template, request, abort

# Import things from Flask that we need.
from accounting import app, db

# Import our models
from models import Contact, Invoice, Policy, Payment
from utils import PolicyAccounting

# Routing for the server.
@app.route("/")
def index():
    # You will need to serve something up here.
    return render_template('index.html')

# Process data
@app.route("/consult_policy", methods=['POST'])
def consult_policy():
    response = {}
    list_invoices = []
    list_payments = []
    data = request.json
    try:
        curr_date = datetime.strptime(data['date'], "%Y-%m-%d")
        policy_id = int(data['policy_id']['id'])
        pa = PolicyAccounting(policy_id)
    except:
        abort(400)

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

    # Get payments
    payments = Payment.query.filter_by(policy_id=policy_id)\
                            .filter(Payment.transaction_date <= curr_date)\
                            .all()
    print len(payments)
    for payment in payments:
        dict_payment = {
            'transaction_date': payment.transaction_date.strftime("%m/%d/%Y"),
            'amount_paid': payment.amount_paid
        }
        list_payments.append(dict_payment)

    response['payments'] = list_payments

    return json.dumps(response)

# Process data
@app.route("/list_policies")
def policy_list():
    response = {}
    list_policies = []
    # Get policies
    policies = Policy.query.order_by(Policy.effective_date) \
                      .all()

    for policy in policies:

        insured = Contact.query.filter_by(id=policy.named_insured).one()
        agent = Contact.query.filter_by(id=policy.agent).one()

        dict_policy = {
            'id': policy.id,
            'policy_number': policy.policy_number,
            'effective_date': policy.effective_date.strftime("%m/%d/%Y"),
            'annual_premium': policy.annual_premium,
            'insured_name': insured.name,
            'agent_name': agent.name
        }
        list_policies.append(dict_policy)

    response['policies'] = list_policies

    return json.dumps(response)

# Process data
@app.route("/users")
def users_data():
    response = {}
    list_agents = []
    list_users = []

    # Get agents
    agents = Contact.query.filter_by(role='Agent').all()

    for agent in agents:
        dict_agent = {
            'id': agent.id,
            'name': agent.name
        }
        list_agents.append(dict_agent)

    # Get users
    users = Contact.query.filter_by(role='Named Insured').all()

    for user in users:
        dict_user = {
            'id': user.id,
            'name': user.name
        }
        list_users.append(dict_user)

    response['agents'] = list_agents
    response['users'] = list_users

    return json.dumps(response)

# Create new policy
@app.route("/create_policy", methods=['POST'])
def create_policy():
    data = request.json
    try:
        curr_date = datetime.strptime(data['date'], "%Y-%m-%d")
        policy_name = data['policy_name']
        existing_insured = data['existingInsured']
        existing_agent = data['existingAgent']
        insured = data['insured']
        agent = data['agent']
        billing_schedule = data['schedule']
        premium = int(data['premium'])
    except:
        abort(400)

    if not existing_insured:
        new_insured = Contact(insured, 'Named Insured')
        db.session.add(new_insured)
        db.session.commit()
        insured = new_insured.id
    else:
        insured = insured['id']

    if not existing_agent:
        new_agent = Contact(agent, 'Agent')
        db.session.add(new_agent)
        db.session.commit()
        agent = new_agent.id
    else:
        agent = agent['id']

    new_policy = Policy(policy_name, curr_date, premium)
    new_policy.billing_schedule = billing_schedule
    new_policy.named_insured = insured
    new_policy.agent = agent
    db.session.add(new_policy)
    db.session.commit()

    return "All good"
