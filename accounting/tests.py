#!/user/bin/env python2.7

import unittest
from datetime import date, datetime
from dateutil.relativedelta import relativedelta

from accounting import db
from models import Contact, Invoice, Payment, Policy
from utils import PolicyAccounting

"""
#######################################################
Test Suite for Accounting
#######################################################
"""

class TestBillingSchedules(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.test_agent = Contact('Test Agent', 'Agent')
        cls.test_insured = Contact('Test Insured', 'Named Insured')
        db.session.add(cls.test_agent)
        db.session.add(cls.test_insured)
        db.session.commit()

        cls.policy = Policy('Test Policy', date(2015, 1, 1), 1200)
        db.session.add(cls.policy)
        cls.policy.named_insured = cls.test_insured.id
        cls.policy.agent = cls.test_agent.id
        db.session.commit()

    @classmethod
    def tearDownClass(cls):
        db.session.delete(cls.test_insured)
        db.session.delete(cls.test_agent)
        db.session.delete(cls.policy)
        db.session.commit()

    def setUp(self):
        pass

    def tearDown(self):
        for invoice in self.policy.invoices:
            db.session.delete(invoice)
        db.session.commit()

    def test_annual_billing_schedule(self):
        self.policy.billing_schedule = "Annual"
        # No invoices currently exist
        self.assertFalse(self.policy.invoices)
        # Invoices should be made when the class is initiated
        pa = PolicyAccounting(self.policy.id)
        self.assertEquals(len(self.policy.invoices), 1)
        self.assertEquals(self.policy.invoices[0].amount_due, self.policy.annual_premium)

    def test_two_pay_billing_schedule(self):
        self.policy.billing_schedule = 'Two-Pay'
        self.assertFalse(self.policy.invoices)
        pa = PolicyAccounting(self.policy.id)
        self.assertEquals(len(self.policy.invoices), 2)
        self.assertEquals(self.policy.invoices[0].amount_due, 600)
        self.assertEquals(sum([invoice.amount_due for invoice in self.policy.invoices]), self.policy.annual_premium)

    def test_monthly_billing_schedule(self):
        self.policy.billing_schedule = 'Monthly'
        self.assertFalse(self.policy.invoices)
        pa = PolicyAccounting(self.policy.id)
        self.assertEqual(len(self.policy.invoices), 12)
        self.assertEqual(self.policy.invoices[0].amount_due, 100)
        self.assertEquals(sum([invoice.amount_due for invoice in self.policy.invoices]), self.policy.annual_premium)


class TestReturnAccountBalance(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.test_agent = Contact('Test Agent', 'Agent')
        cls.test_insured = Contact('Test Insured', 'Named Insured')
        db.session.add(cls.test_agent)
        db.session.add(cls.test_insured)
        db.session.commit()

        cls.policy = Policy('Test Policy', date(2015, 1, 1), 1200)
        cls.policy.named_insured = cls.test_insured.id
        cls.policy.agent = cls.test_agent.id
        db.session.add(cls.policy)
        db.session.commit()

    @classmethod
    def tearDownClass(cls):
        db.session.delete(cls.test_insured)
        db.session.delete(cls.test_agent)
        db.session.delete(cls.policy)
        db.session.commit()

    def setUp(self):
        self.payments = []

    def tearDown(self):
        for invoice in self.policy.invoices:
            db.session.delete(invoice)
        for payment in self.payments:
            db.session.delete(payment)
        db.session.commit()

    def test_annual_on_eff_date(self):
        self.policy.billing_schedule = "Annual"
        pa = PolicyAccounting(self.policy.id)
        self.assertEquals(pa.return_account_balance(date_cursor=self.policy.effective_date), 1200)

    def test_two_pay_on_eff_date(self):
        self.policy.billing_schedule = "Two-Pay"
        pa = PolicyAccounting(self.policy.id)
        self.assertEquals(pa.return_account_balance(date_cursor=self.policy.effective_date), 600)

    def test_two_pay_on_last_installment_bill_date(self):
        self.policy.billing_schedule = "Two-Pay"
        pa = PolicyAccounting(self.policy.id)
        invoices = Invoice.query.filter_by(policy_id=self.policy.id)\
                                .order_by(Invoice.bill_date).all()
        self.assertEquals(pa.return_account_balance(date_cursor=invoices[-1].bill_date), 1200)

    def test_two_pay_account_balance(self):
        self.policy.billing_schedule = "Two-Pay"
        pa = PolicyAccounting(self.policy.id)
        invoices = Invoice.query.filter_by(policy_id=self.policy.id)\
                                .order_by(Invoice.bill_date).all()
        # An index is used instead of iterate directly on the elements to help with the balance calculation
        for curr_invoice in range(len(invoices)):
            self.assertEquals(pa.return_account_balance(date_cursor=invoices[curr_invoice].bill_date),
                              (curr_invoice + 1) * invoices[curr_invoice].amount_due)

    def test_two_pay_payments_and_balance(self):
        self.policy.billing_schedule = "Two-Pay"
        pa = PolicyAccounting(self.policy.id)
        invoices = Invoice.query.filter_by(policy_id=self.policy.id)\
                                .order_by(Invoice.bill_date).all()
        for invoice in invoices:
            self.assertEquals(pa.return_account_balance(date_cursor=invoice.bill_date), invoice.amount_due)
            self.payments.append(pa.make_payment(contact_id=self.policy.named_insured,
                                                 date_cursor=invoice.bill_date, amount=invoice.amount_due))
            self.assertEquals(pa.return_account_balance(date_cursor=invoice.bill_date), 0)

    def test_quarterly_on_eff_date(self):
        self.policy.billing_schedule = "Quarterly"
        pa = PolicyAccounting(self.policy.id)
        self.assertEquals(pa.return_account_balance(date_cursor=self.policy.effective_date), 300)

    def test_quarterly_on_last_installment_bill_date(self):
        self.policy.billing_schedule = "Quarterly"
        pa = PolicyAccounting(self.policy.id)
        invoices = Invoice.query.filter_by(policy_id=self.policy.id)\
                                .order_by(Invoice.bill_date).all()
        self.assertEquals(pa.return_account_balance(date_cursor=invoices[3].bill_date), 1200)

    def test_quarterly_on_second_installment_bill_date_with_full_payment(self):
        self.policy.billing_schedule = "Quarterly"
        pa = PolicyAccounting(self.policy.id)
        invoices = Invoice.query.filter_by(policy_id=self.policy.id)\
                                .order_by(Invoice.bill_date).all()
        self.payments.append(pa.make_payment(contact_id=self.policy.named_insured,
                                             date_cursor=invoices[1].bill_date, amount=600))
        self.assertEquals(pa.return_account_balance(date_cursor=invoices[1].bill_date), 0)

    def test_monthly_on_eff_date(self):
        self.policy.billing_schedule = "Monthly"
        pa = PolicyAccounting(self.policy.id)
        self.assertEquals(pa.return_account_balance(date_cursor=self.policy.effective_date), 100)

    def test_monthly_on_last_installment_bill_date(self):
        self.policy.billing_schedule = "Monthly"
        pa = PolicyAccounting(self.policy.id)
        invoices = Invoice.query.filter_by(policy_id=self.policy.id)\
                                .order_by(Invoice.bill_date).all()
        self.assertEquals(pa.return_account_balance(date_cursor=invoices[-1].bill_date), 1200)

    def test_monthly_account_balance(self):
        self.policy.billing_schedule = "Monthly"
        pa = PolicyAccounting(self.policy.id)
        invoices = Invoice.query.filter_by(policy_id=self.policy.id)\
                                .order_by(Invoice.bill_date).all()
        # An index is used instead of iterate directly on the elements to help with the balance calculation
        for curr_invoice in range(len(invoices)):
            self.assertEquals(pa.return_account_balance(date_cursor=invoices[curr_invoice].bill_date),
                              (curr_invoice + 1) * invoices[curr_invoice].amount_due)

    def test_monthly_payments_and_balance(self):
        self.policy.billing_schedule = "Monthly"
        pa = PolicyAccounting(self.policy.id)
        invoices = Invoice.query.filter_by(policy_id=self.policy.id)\
                                .order_by(Invoice.bill_date).all()
        for invoice in invoices:
            self.assertEquals(pa.return_account_balance(date_cursor=invoice.bill_date), invoice.amount_due)
            self.payments.append(pa.make_payment(contact_id=self.policy.named_insured,
                                                 date_cursor=invoice.bill_date, amount=invoice.amount_due))
            self.assertEquals(pa.return_account_balance(date_cursor=invoice.bill_date), 0)
