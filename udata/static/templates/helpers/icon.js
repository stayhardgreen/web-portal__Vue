define(['hbs/handlebars'], function(Handlebars) {

    Handlebars.registerHelper('icon', function(value, options) {
        var cls = value.indexOf('fa-') == 0 ? 'fa '+ value : 'glyphicon glyphicon-' + value;

        if ($.inArray('cls', options.hash)) {
            cls = [cls, options.hash['cls']].join(' ');
        }

        return new Handlebars.SafeString('<span class="' + cls + '"></span>');
    });

});
