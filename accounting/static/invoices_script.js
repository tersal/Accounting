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
    self.date = ko.observable();
    self.policy_id = ko.observable();
    self.amount_due = ko.observable(0);
    self.invoices = ko.observableArray([]);

    // Send current policy information to the server
    self.consult = function() {
        $.ajax({
            url: "/consult_policy",
            type: 'POST',
            contentType: 'application/json',
            dataType: 'json',
            data: ko.toJSON({ date: self.date, policy_id: self.policy_id }),
        }).done(function(response) {
            self.amount_due(response.total_balance);
            self.invoices([])
            for(var i = 0; i < response.invoices.length; i++) {
                invoice = {
                    bill_date: response.invoices[i].bill_date,
                    due_date: response.invoices[i].due_date,
                    cancel_date: response.invoices[i].cancel_date,
                    amount_due: response.invoices[i].amount_due,
                }
                self.invoices.push(invoice);
            }
        })
    };
}

// Activate knockout.js
ko.applyBindings(new PolicyViewModel());

});

