define(['api', 'models/base_list', 'vue', 'moment', 'jquery'], function(API, ModelList, Vue, moment, $) {
    'use strict';

    var Metrics = ModelList.extend({
        name: 'Metrics',
        ns: 'site',
        fetch: 'metrics_for',
        methods: {
            /**
             * Consolidate data
             */
            timeserie: function(series) {
                if (!this.items || !this.items.length) {
                    return [];
                }

                var names = series || Object.keys(last_item.values),
                    data = [],
                    values = {},
                    previous= {};

                // Extract values
                for (var i=0; i < this.items.length; i++) {
                    var item = this.items[i];
                    values[item.date] = item.values;
                }

                var sorted = Object.keys(values).sort(),
                    first_date = sorted[0],
                    last_date = sorted[sorted.length -1],
                    start = moment(first_date),
                    end = moment(last_date),
                    days = end.diff(start, 'days');


                for (i=0; i <= days; i++) {
                    var date = start.clone().add(i, 'days'),
                        key = date.format('YYYY-MM-DD'),
                        row = {date: date, key: key};

                    names.forEach(function(name) {
                        if (values.hasOwnProperty(key) && values[key].hasOwnProperty(name)) {
                            row[name] = values[key][name];
                        } else if (previous.hasOwnProperty(name)) {
                            row[name] = previous[name];
                        } else {
                            row[name] = 0;
                        }
                    });

                    previous = row;
                    data.push(row);
                }

                return data;
            }
        }
    });

    return Metrics;
});
