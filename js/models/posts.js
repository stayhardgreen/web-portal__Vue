import {ModelPage} from 'models/base';
import log from 'logger';


export default class PostPage extends ModelPage {
    constructor(options) {
        super(options);
        this.$options.ns = 'posts';
        this.$options.fetch = 'list_posts';
    }
};
