var path = require('path');
var webpack = require('webpack');
var HtmlWebpackPlugin = require('html-webpack-plugin');
var VueLoaderPlugin = require('vue-loader/lib/plugin');

module.exports = {
    entry: ['./src/main.scss', './src/app.js'],
    plugins: [
        new VueLoaderPlugin(),
        new webpack.ProvidePlugin({
            _: 'lodash'
        }),
        new HtmlWebpackPlugin({
            template: './src/index.html',
        })
    ],
    resolve: {
        modules: [path.resolve(__dirname, 'src'), 'node_modules'],
        extensions: [ '.js', '.vue' ],
        alias: {
            vue$: 'vue/dist/vue.esm.js',
        }
    },
    module: {
        rules: [
            {
                test: /\.vue$/,
                loader: 'vue-loader'
            },
            {
                test: /\.scss$/,
                use: [
                    'vue-style-loader',
                    'css-loader',
                    'sass-loader'
                ]
            },
            {
                test: /\.gif$/,
                loader: 'file-loader',
                options: {
                    outputPath: 'assets',
                    publicPath: 'assets'
                },
            },
        ]
    },
    watchOptions: {
        aggregateTimeout: 600,
        poll: 3000
    },
    devServer: {
        port: 8788,
        host: '0.0.0.0',
        hot: true
    }
};