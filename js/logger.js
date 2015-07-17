define(['vendor/normalizeconsole'], function() {
    var DEBUG = false,
        Logger = {};
    //>>excludeStart('production', pragmas.production);
    DEBUG = true;
    //>>excludeEnd('production');

    Logger.info = Function.prototype.bind.call(console.info, console);
    Logger.warn = Function.prototype.bind.call(console.warn, console);
    Logger.error = Function.prototype.bind.call(console.error, console);

    if (DEBUG) {
        Logger.log = Function.prototype.bind.call(console.log, console);
        Logger.debug = Function.prototype.bind.call(console.debug, console);
    } else {
        Logger.log = Logger.debug = function() {};
    }

    return Logger;
});
