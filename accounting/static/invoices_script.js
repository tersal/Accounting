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
    self.policy_id = ko.observable().extend({ required: true });
    self.amount_due = ko.observable(0);
    self.invoices = ko.observableArray([]);
    self.policies = ko.observableArray([]);
    self.payments = ko.observableArray([]);
    self.errors = ko.validation.group(this);
    self.payment_amount = ko.observable();
    // Visibility variables
    self.visiblePolicies = ko.observable(true);
    self.visibleNewPolicy = ko.observable(false);
    self.visibleInvoices = ko.observable(false);
    // New policy handling
    self.existingInsured = ko.observable(false);
    self.existingAgent = ko.observable(false);
    self.agents = ko.observableArray([]);
    self.insureds = ko.observableArray([]);
    self.newPolicyAgent = ko.observable();
    self.newPolicyInsured = ko.observable();
    self.newPolicyDate = ko.observable();
    self.newPolicyName = ko.observable();
    self.newPolicyPremium = ko.observable();
    self.newPolicyBilling = ko.observable();

    self.billingSchedules = [
        "Annual",
        'Quarterly',
        "Two-Pay",
        "Monthly"
    ];

    self.togglePolicies = function() {
        self.consult_policies();
        self.visiblePolicies(!self.visiblePolicies());
        self.visibleInvoices(false);
        self.visibleNewPolicy(false);
    };

    self.toggleInvoices = function() {
        self.visibleInvoices(!self.visibleInvoices());
        self.visiblePolicies(false);
        self.visibleNewPolicy(false);
    };

    self.toggleNewPolicy = function() {
        self.visibleNewPolicy(!self.visibleNewPolicy());
        self.visibleInvoices(false);
        self.visiblePolicies(false);
        self.agents([]);
        self.insureds([]);
        $.getJSON("/users", function(response) {
            if(!response.hasOwnProperty('agents') ||
               !response.hasOwnProperty('users')) {
                return;
            }
            for(var i = 0; i < response.agents.length; i++) {
                agent = {
                    id: response.agents[i].id,
                    name: response.agents[i].name
                }
                self.agents.push(agent);
            }
            for(var i = 0; i < response.users.length; i++) {
                user = {
                    id: response.users[i].id,
                    name: response.users[i].name
                }
                self.insureds.push(user);
            }
        });
    };

    self.existingAgent.subscribe(function(value) {
        if(value) {
            self.newPolicyAgent = ko.observable();
        }
    }, this, "beforeChange");

    self.existingInsured.subscribe(function(value) {
        if(value) {
            self.newPolicyInsured = ko.observable();
        }
    }, this, "beforeChange");

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

    self.make_payment = function() {
        $.ajax({
            url: "/make_payment",
            type: 'POST',
            contentType: 'application/json',
            data : ko.toJSON({ date: self.date, payment_amount: self.payment_amount, policy_id : self.policy_id}),
        }).done(function(response) {
            alert("Success");
            self.consult()
        }).fail(function() {
            alert('Failure')
        });
    }

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
                self.policies([]);
                for(var i = 0; i < response.policies.length; i++) {
                    policy = {
                        id: response.policies[i].id,
                        effective_date: response.policies[i].effective_date,
                        policy_number: response.policies[i].policy_number,
                        annual_premium: response.policies[i].annual_premium,
                        insured_name: response.policies[i].insured_name,
                        agent_name: response.policies[i].agent_name
                    }
                    self.policies.push(policy);
                }
            }).fail(function() {
                alert("Request Failed");
            });
    };

    // Create a new policy with the provided data
    self.create_policy = function() {
        $.ajax({
                url: "/create_policy",
                type: 'POST',
                contentType: 'application/json',
                data: ko.toJSON({ date: self.newPolicyDate, policy_name: self.newPolicyName,
                                  existingInsured : self.existingInsured, existingAgent: self.existingAgent,
                                  insured: self.newPolicyInsured, agent: self.newPolicyAgent,
                                  premium: self.newPolicyPremium, schedule: self.newPolicyBilling}),
            }).done(function(response) {
                self.existingInsured(false);
                self.existingAgent(false);
                self.newPolicyAgent("");
                self.newPolicyInsured("");
                self.newPolicyDate("");
                self.newPolicyName("");
                self.newPolicyPremium("");
                self.newPolicyBilling("Annual");
                alert("Policy Created");
            }).fail(function() {

            });

    };

    $.getJSON("/list_policies", function(response) {
        if(!response.hasOwnProperty('policies')) {
            return;
        }
        for(var i = 0; i < response.policies.length; i++) {
            policy = {
                id: response.policies[i].id,
                effective_date: response.policies[i].effective_date,
                policy_number: response.policies[i].policy_number,
                annual_premium: response.policies[i].annual_premium,
                insured_name: response.policies[i].insured_name,
                agent_name: response.policies[i].agent_name
            }
            self.policies.push(policy);
        }
    });


}

// Activate knockout.js
ko.applyBindings(new PolicyViewModel());

});
