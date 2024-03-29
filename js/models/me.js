import User from 'models/user';
import Raven from 'raven';
import config from 'config';

class Me extends User {
    fetch() {
        this.loading = true;
        this.$api('me.get_me', {}, this.on_user_fetched);
        return this;
    }

    update(data, on_error) {
        this.loading = true;
        this.$api('me.update_me', {payload: JSON.stringify(data)}, this.on_fetched, this.on_error(on_error));
    }

    on_user_fetched(response) {
        if (config.sentry) {
            Raven.setUserContext({
                id: response.obj.id,
                is_authenticated: true,
                is_anonymous: false
            });
        }
        this.on_fetched(response);
    }
}

const me = new Me();

export default me.fetch();
