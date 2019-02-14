#!/user/bin/env python2.7

from datetime import date, datetime
from dateutil.relativedelta import relativedelta

from accounting import db
from models import Contact, Invoice, Payment, Policy

"""
#######################################################
This is the base code for the engineer project.
#######################################################
"""

class PolicyAccounting(object):
    """
     Each policy has its own instance of accounting.

     :param policy_id: The identifier of the policy whose data will be used.
     :type  policy_id: int
     :ivar  policy:    Local variable used to store the policy that is obtained from the database.
     :vartype policy:  Policy object
    """
    def __init__(self, policy_id):
        try:
            self.policy = Policy.query.filter_by(id=policy_id).one()
        except:
            raise ValueError("No Policy was found with that ID")

        if not self.policy.invoices:
            # The invoices are created at this point, according to the billing schedule, the annual premium
            # is divided equally according to the number of payments
            print "Creating invoices for Policy %d" % policy_id
            self.make_invoices()

    def return_account_balance(self, date_cursor=None):
        """Calculate the pending balance in a policy.

        This function calculates the balance of this policy according to the date provided and the number of
        payments already performed.

        :param date_cursor: Date used as basis for the balance calculation, if omitted, current date is used.
        :type date_cursor: datetime.date object
        :returns: int -- Amount due until the date specified
        """
        if not date_cursor:
            date_cursor = datetime.now().date()
            print "No date provided, today date will be used: " + str(date_cursor)

        # Get the invoices from the database whose bill date is earlier or equal to the date provided.
        invoices = Invoice.query.filter_by(policy_id=self.policy.id)\
                                .filter(Invoice.bill_date <= date_cursor)\
                                .filter(Invoice.deleted == False)\
                                .order_by(Invoice.bill_date)\
                                .all()
        print "Number of due Invoices: %d" % len(invoices)
        due_now = 0
        # Calculate the sum of all the invoices until the specified date
        for invoice in invoices:
            due_now += invoice.amount_due

        # Get all the payments that were performed to this policy based on the date provided
        payments = Payment.query.filter_by(policy_id=self.policy.id)\
                                .filter(Payment.transaction_date <= date_cursor)\
                                .all()
        print "Number if payments: %d" % len(payments)
        # Subtract the payments already performed to this policy.
        for payment in payments:
            due_now -= payment.amount_paid

        print "Total amount due: %d" % due_now
        return due_now

    def make_payment(self, contact_id=None, date_cursor=None, amount=0):
        """Registers a payment to a policy

        This function registers a payment in the specified date, if no date is specified
        then the current date is used.
        :param contact_id: Name of the insured. (default = None)
        :type  contact_id: str
        :param date_cursor: Date when the payment was registered. (default = None)
        :type  date_cursor: datetime.date
        :param amount: Amount of the payment to be registered. (default = 0)
        :type  amount: int
        :returns: Payment -- Payment class created with the provided data or None if it wasn't possible to make
                             the payment.
        """
        if not date_cursor:
            date_cursor = datetime.now().date()
            print "No date provided, today date will be used: " + str(date_cursor)

        # If no name is provided for the insured, use the one stored in the policy
        if not contact_id:
            if not self.policy.named_insured:
                # Return if no name was found in the parameter passed to the function
                # or in the policy for the named_insured
                print "Missing contact identifier for this payment, aborting payment."
                return
            else:
                contact_id = self.policy.named_insured

        payment = Payment(self.policy.id,
                          contact_id,
                          amount,
                          date_cursor)
        db.session.add(payment)
        db.session.commit()

        return payment

    def evaluate_cancellation_pending_due_to_non_pay(self, date_cursor=None):
        """Evaluates the cancellation status of an invoice

         If this function returns true, an invoice
         on a policy has passed the due date without
         being paid in full. However, it has not necessarily
         made it to the cancel_date yet.

         :param date_cursor: The date used to verify the current status of the policy. (default = None)
         :type  date_cursor: datetime.date
         :returns: True  -- An invoice has passed the due date but still not in the cancel_date
                   False -- No invoice has passed the due date without payment.
        """
        if not date_cursor:
            date_cursor = datetime.now().date()
            print "No date provided, today date will be used: " + str(date_cursor)

        # Get all the invoices that are beyond the due date but still not passed their cancel date
        invoice = Invoice.query.filter_by(policy_id=self.policy.id)\
                               .filter(Invoice.due_date < date_cursor)\
                               .filter(Invoice.cancel_date > date_cursor)\
                               .filter(Invoice.deleted == False)\
                               .order_by(Invoice.bill_date)\
                               .all()
        # If the date provided does not match any Invoice range, we assume that
        # there are not pending cancellations.
        if len(invoice) is 0:
            return False

        # We need to get all the invoices that were billed with and before the
        # one that is in the cancellation range to avoid accounting for an
        # invoice that was just billed but still not passed the due date.
        invoices = Invoice.query.filter_by(policy_id=self.policy.id)\
                                .filter(Invoice.bill_date <= invoice[0].bill_date)\
                                .filter(Invoice.deleted == False)\
                                .order_by(Invoice.bill_date)\
                                .all()
        # In contrast we get all the payments until the date_cursor, this is to
        # include the payments made after the bill date and before the due date
        payments = Payment.query.filter_by(policy_id=self.policy.id)\
                                .filter(Payment.transaction_date <= date_cursor)\
                                .all()

        due_now = 0
        for curr_invoice in invoices:
            due_now += curr_invoice.amount_due

        for payment in payments:
            due_now -= payment.amount_paid

        return due_now > 0


    def evaluate_cancel(self, date_cursor=None, cancellation_reason=None):
        """Evaluates if a policy should be canceled.

        :param date_cursor: The date used to verify if this policy should be canceled. (default = None)
        :type  date_cursor: datetime.date
        :param cancellation_reason: Used to define if this policy should be canceled for a reason
                                    different than lack of payment
        :type  cancellation_reason: str
        """
        if not date_cursor:
            date_cursor = datetime.now().date()
            print "No date provided, today date will be used: " + str(date_cursor)

        # Validate if the cancellation reason is other than lack of payment
        if not cancellation_reason:
            # Get the invoices that are ready to be canceled.
            invoices = Invoice.query.filter_by(policy_id=self.policy.id)\
                                    .filter(Invoice.cancel_date <= date_cursor)\
                                    .filter(Invoice.deleted == False)\
                                    .order_by(Invoice.bill_date)\
                                    .all()

            if len(invoices) is 0:
                # If no invoices are past the cancellation date, nothing else to do
                return

            due_now = 0
            # We get the sum of all that is due of the invoices that passed the
            # cancellation date.
            for invoice in invoices:
                due_now += invoice.amount_due

            # We get all the payments until before the last invoice cancellation
            # date
            payments = Payment.query.filter_by(policy_id=self.policy.id)\
                                    .filter(Payment.transaction_date < invoices[-1].cancel_date)\
                                    .all()

            for payment in payments:
                due_now -= payment.amount_paid

            # If some amount is still pending, then we can cancel the policy.
            if due_now > 0:
                print "This policy will be canceled due lack of payment"
                self.policy.status = "Canceled"
                self.policy.cancel_date = date_cursor
                self.policy.cancel_reason = "Lack of payment"

        else:
            # We assume that the cancel reason provided is valid
            print "This policy will be canceled due: " + cancellation_reason
            self.policy.status = "Canceled"
            self.policy.cancel_date = date_cursor
            self.policy.cancel_reason = cancellation_reason

        if self.policy.status is "Canceled":
            db.session.add(self.policy)
            db.session.commit()


    def make_invoices(self):
        """Create invoices for this policy.

        This function creates invoices for this policy according to the billing schedule and the total annual
        premium of the policy.

        The total annual premium of the policy is divided equally between the different the periods created
        according to the billing schedule.

        If there are invoices already created for this policy, the old invoices will be marked as deleted
        and not be accounted for any other operation on this policy, new invoices will be generated.

        The invoices are stored in the database and are related to the policy through the policy id.
        """

        invoices = []

        # If there are pending invoices, they will be marked as "deleted" since we assume that the user
        # made changes to the policy and rendered the previous invoices invalid.
        for invoice in self.policy.invoices:
            print "Deleting current invoices of this policy prior to the creation of new ones."
            invoice.deleted = True
            invoices.append(invoice)

        billing_schedules = {'Annual': None, 'Two-Pay': 2, 'Quarterly': 4, 'Monthly': 12}

        # Create the first invoice based on the effective date.
        first_invoice = Invoice(self.policy.id,
                                self.policy.effective_date, #bill_date
                                self.policy.effective_date + relativedelta(months=1), #due
                                self.policy.effective_date + relativedelta(months=1, days=14), #cancel
                                self.policy.annual_premium)
        invoices.append(first_invoice)

        if self.policy.billing_schedule == "Annual":
            # Since only one invoice is needed for this billing schedule and was already created previously,
            # nothing else is needed.
            pass
        elif self.policy.billing_schedule == "Two-Pay":
            first_invoice.amount_due = first_invoice.amount_due / billing_schedules.get(self.policy.billing_schedule)
            for i in range(1, billing_schedules.get(self.policy.billing_schedule)):
                # In a Two-Pay schedule only one invoices is needed after 6 months of the initial invoice.
                months_after_eff_date = i*6
                bill_date = self.policy.effective_date + relativedelta(months=months_after_eff_date)
                invoice = Invoice(self.policy.id,
                                  bill_date,
                                  bill_date + relativedelta(months=1),
                                  bill_date + relativedelta(months=1, days=14),
                                  self.policy.annual_premium / billing_schedules.get(self.policy.billing_schedule))
                invoices.append(invoice)
        elif self.policy.billing_schedule == "Quarterly":
            first_invoice.amount_due = first_invoice.amount_due / billing_schedules.get(self.policy.billing_schedule)
            for i in range(1, billing_schedules.get(self.policy.billing_schedule)):
                # For the Quarterly schedule, an invoice is created for every three months period
                months_after_eff_date = i*3
                bill_date = self.policy.effective_date + relativedelta(months=months_after_eff_date)
                invoice = Invoice(self.policy.id,
                                  bill_date,
                                  bill_date + relativedelta(months=1),
                                  bill_date + relativedelta(months=1, days=14),
                                  self.policy.annual_premium / billing_schedules.get(self.policy.billing_schedule))
                invoices.append(invoice)
        elif self.policy.billing_schedule == "Monthly":
            first_invoice.amount_due = first_invoice.amount_due / billing_schedules.get(self.policy.billing_schedule)
            for i in range(1, billing_schedules.get(self.policy.billing_schedule)):
                # In a monthly schedule, twelve invoices should be created.
                months_after_eff_date = i
                bill_date = self.policy.effective_date + relativedelta(months=months_after_eff_date)
                invoice = Invoice(self.policy.id,
                                  bill_date,
                                  bill_date + relativedelta(months=1),
                                  bill_date + relativedelta(months=1, days=14),
                                  self.policy.annual_premium / billing_schedules.get(self.policy.billing_schedule))
                invoices.append(invoice)
        else:
            print "You have chosen a bad billing schedule."

        for invoice in invoices:
            db.session.add(invoice)
        db.session.commit()

################################
# The functions below are for the db and
# shouldn't need to be edited.
################################
def build_or_refresh_db():
    db.drop_all()
    db.create_all()
    insert_data()
    print "DB Ready!"

def insert_data():
    #Contacts
    contacts = []
    john_doe_agent = Contact('John Doe', 'Agent')
    contacts.append(john_doe_agent)
    john_doe_insured = Contact('John Doe', 'Named Insured')
    contacts.append(john_doe_insured)
    bob_smith = Contact('Bob Smith', 'Agent')
    contacts.append(bob_smith)
    anna_white = Contact('Anna White', 'Named Insured')
    contacts.append(anna_white)
    joe_lee = Contact('Joe Lee', 'Agent')
    contacts.append(joe_lee)
    ryan_bucket = Contact('Ryan Bucket', 'Named Insured')
    contacts.append(ryan_bucket)

    for contact in contacts:
        db.session.add(contact)
    db.session.commit()

    policies = []
    p1 = Policy('Policy One', date(2015, 1, 1), 365)
    p1.billing_schedule = 'Annual'
    p1.named_insured = john_doe_insured.id
    p1.agent = bob_smith.id
    policies.append(p1)

    p2 = Policy('Policy Two', date(2015, 2, 1), 1600)
    p2.billing_schedule = 'Quarterly'
    p2.named_insured = anna_white.id
    p2.agent = joe_lee.id
    policies.append(p2)

    p3 = Policy('Policy Three', date(2015, 1, 1), 1200)
    p3.billing_schedule = 'Monthly'
    p3.named_insured = ryan_bucket.id
    p3.agent = john_doe_agent.id
    policies.append(p3)

    p4 = Policy('Policy Four', date(2015, 2, 1), 500)
    p4.billing_schedule = 'Two-Pay'
    p4.named_insured = ryan_bucket.id
    p4.agent = john_doe_agent.id
    policies.append(p4)

    for policy in policies:
        db.session.add(policy)
    db.session.commit()

    for policy in policies:
        PolicyAccounting(policy.id)

    payment_for_p2 = Payment(p2.id, anna_white.id, 400, date(2015, 2, 1))
    db.session.add(payment_for_p2)
    db.session.commit()
