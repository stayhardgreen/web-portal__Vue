var path = require('path');
var webpack = require('webpack');

var ExtractTextPlugin = require('extract-text-webpack-plugin');
var node_path = path.join(__dirname, 'node_modules');

var vue = require('vue-loader'),
    css_loader = ExtractTextPlugin.extract('style', 'css?sourceMap'),
    less_loader = ExtractTextPlugin.extract('style', 'css?sourceMap!less?sourceMap=source-map-less-inline');

var languages = ['en', 'es', 'fr'];

module.exports = {
    entry: {
        site: './js/site.js',
        home: './js/home.js',
        search: './js/search.js',
        'dataset/display': './js/dataset/display',
        'reuse/display': './js/reuse/display',
        'organization/display': './js/organization/display',
        'dashboard/site': './js/dashboard/site',
        'dashboard/organization': './js/dashboard/organization',
    },
    output: {
        path: path.join(__dirname, 'udata', 'static'),
        publicPath: "/static/",
        filename: "[name].js"
    },
    resolve: {
        root: [
            __dirname,
            path.join(__dirname, 'js'),
        ],
        alias: {
            'jquery-slimscroll': path.join(node_path, 'jquery-slimscroll/jquery.slimscroll'),
            'fineuploader': path.join(node_path, 'fine-uploader/fine-uploader/fine-uploader'),
            'bloodhound': path.join(node_path, 'typeahead.js/dist/bloodhound'),
            'typeahead': path.join(node_path, 'typeahead.js/dist/typeahead.jquery'),
            'handlebars': 'handlebars/runtime.js',
        }
    },
    devtools: 'eval-source-map',
    module: {
        loaders: [
            {test: /\.(jpg|jpeg|png|gif|svg)$/, loader: 'file'},
            {test: /\.css$/, loader: css_loader},
            {test: /\.less$/, loader: less_loader},
            {test: /\.vue$/, loader: vue.withLoaders({css: css_loader, less: less_loader})},
            {test: /\.json$/, loader: "json"},
            {test: /\.hbs$/, loader: 'handlebars?debug=true&helperDirs[]=' + path.join(__dirname, 'js', 'templates', 'helpers')},
            {test: /\.html$/, loader: 'html'},
            {test: /\.(woff|svg|ttf|eot|otf)([\?]?.*)$/, loader: "file-loader?name=[name].[ext]"},
        ]
    },
    plugins: [
        // Fix AdminLTE packaging
        new webpack.NormalModuleReplacementPlugin(
            /admin-lte\/build\/img\/boxed-bg\.jpg$/,
            'admin-lte/dist/img/boxed-bg.jpg'
        ),
        // new webpack.ContextReplacementPlugin(/admin-lte\/build\/img\/.*$/, 'admin-lte/dist/img/$1'),
        new webpack.ProvidePlugin({
            $: 'jquery',
            jQuery: 'jquery',
            'window.jQuery': 'jquery',
        }),
        new ExtractTextPlugin('[name].css'),
        new webpack.IgnorePlugin(/^(\.\/)?shred/),
        new webpack.ContextReplacementPlugin(/moment\/locale$/, new RegExp(languages.join('|'))),
        new webpack.ContextReplacementPlugin(/locales$/, new RegExp(languages.join('|'))),
        new webpack.optimize.CommonsChunkPlugin('common.js')
    ]
};
