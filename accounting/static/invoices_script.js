$(document).ready(function() {

ko.bindingHandlers.fadeVisible = {
    init: function(element, valueAccessor) {
        // Start visible/invisible according to initial value
        var shouldDisplay = valueAccessor();
        $(element).toggle(shouldDisplay);
    },
    update: function(element, valueAccessor) {
        // On update, fade in/out
        var shouldDisplay = valueAccessor();
        shouldDisplay ? $(element).fadeIn() : $(element).fadeOut();
    }
};

function PolicyViewModel() {
    // Data
    var self = this;
    self.date = ko.observable().extend({ required: true, date: true });
    self.policy_id = ko.observable().extend({ required: true, number: true });
    self.amount_due = ko.observable(0);
    self.invoices = ko.observableArray([]);
    self.policies = ko.observableArray([]);
    self.payments = ko.observableArray([]);
    self.errors = ko.validation.group(this);

    // Send current policy information to the server
    self.consult = function() {
        if(self.errors().length == 0) {
            $.ajax({
                url: "/consult_policy",
                type: 'POST',
                contentType: 'application/json',
                dataType: 'json',
                data: ko.toJSON({ date: self.date, policy_id: self.policy_id }),
            }).done(function(response) {
                if(!response.hasOwnProperty('total_balance') ||
                   !response.hasOwnProperty('invoices') ||
                   !response.hasOwnProperty('payments')) {
                   alert("Incorrect data received from server");
                   return;
                }
                self.amount_due(response.total_balance);
                self.invoices([]);
                self.policies([]);
                self.payments([]);
                // Process invoices list
                for(var i = 0; i < response.invoices.length; i++) {
                    invoice = {
                        bill_date: response.invoices[i].bill_date,
                        due_date: response.invoices[i].due_date,
                        cancel_date: response.invoices[i].cancel_date,
                        amount_due: response.invoices[i].amount_due,
                    }
                    self.invoices.push(invoice);
                }
                // Process payments list
                for(var i = 0; i < response.payments.length; i++) {
                    payment = {
                        transaction_date: response.payments[i].transaction_date,
                        amount_paid: response.payments[i].amount_paid
                    }
                    self.payments.push(payment);
                }
            }).fail(function() {
                alert("Request Failed: The input values are correct?");
            });
        } else {
            alert("Please check the input values.");
        }
    };

        // Send current policy information to the server
    self.consult_policies = function() {
            $.ajax({
                url: "/list_policies",
                type: 'GET',
                dataType: 'json',
            }).done(function(response) {
                if(!response.hasOwnProperty('policies')) {
                    alert("Incorrect data received from server.");
                    return;
                }
                self.amount_due(0);
                self.invoices([]);
                self.policies([]);
                self.payments([]);
                for(var i = 0; i < response.policies.length; i++) {
                    policy = {
                        id: response.policies[i].id,
                        effective_date: response.policies[i].effective_date,
                        policy_number: response.policies[i].policy_number,
                        annual_premium: response.policies[i].annual_premium,
                    }
                    self.policies.push(policy);
                }
            }).fail(function() {
                alert("Request Failed");
            });
        }
}

// Activate knockout.js
ko.applyBindings(new PolicyViewModel());

});
