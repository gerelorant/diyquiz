import os
from flask_migrate import init, migrate, upgrade

from app import app
import model


if __name__ == '__main__':
    with app.app_context():
        if not os.path.exists(app.config.get('MIGRATE_DIRECTORY', 'data/migrations')):
            init()
        migrate()
        upgrade()

        admin_role = model.Role.query.filter_by(name='admin').first()
        if admin_role is None:
            admin_role = model.Role()
            admin_role.name = 'admin'
            model.db.session.add(admin_role)
            model.db.session.commit()

        admin_user = model.User.query.filter_by(username='admin').first()
        if admin_user is None:
            admin_user = model.User()
            admin_user.username = 'admin'
            admin_user.email = app.config.get('MAIL_DEFAULT_SENDER', None)
            admin_user.set_password('Admin.21')
            admin_user.roles.append(admin_role)
            model.db.session.add(admin_user)
            model.db.session.commit()
