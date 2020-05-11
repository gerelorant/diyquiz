import datetime as dt
import random
import typing

from flask_security import UserMixin, RoleMixin
from flask_security.utils import verify_password, hash_password
from flask_sqlalchemy import SQLAlchemy, Model
from Levenshtein import distance as str_distance
import sqlalchemy as sa
from sqlalchemy.ext.declarative import declared_attr


class BaseModel(Model):
    id_length = 9

    @classmethod
    def generate_id(cls):
        while True:
            new_id = random.randint(10**(cls.id_length-1), 10**cls.id_length-1)
            if cls.query.get(new_id) is None:
                return new_id

    @declared_attr
    def id(cls):
        return sa.Column(sa.Integer, default=cls.generate_id, primary_key=True, autoincrement=False)

    @classmethod
    def load_csv(
            cls,
            path: str,
            separator: str = ';',
            newline: str = '\n',
            encoding: str = 'utf8') -> typing.Generator[dict, None, None]:
        with open(path, encoding=encoding) as f:
            data = f.read()

        return cls.load_text(data, separator, newline)

    @classmethod
    def load_text(cls, data: str, separator: str = ';', newline: str = '\n') -> typing.Generator[dict, None, None]:
        if data.startswith('\ufeff') or data.startswith('\ufffe'):
            data = data[1:]

        lines = [x.strip() for x in data.split(newline)]
        headers = [x.strip() for x in lines[0].split(separator)]
        for line in lines[1:]:
            if not line:
                continue

            values = [x.strip() for x in line.split(separator)]

            kwargs = {}
            for i, name in enumerate(headers):
                kwargs[name] = values[i]

            yield kwargs

    def update(self, **kwargs):
        for (k, v) in kwargs.items():
            if isinstance(v, str) and not v:
                continue
            setattr(self, k, v)

    @classmethod
    def update_or_create(cls, **kwargs):
        pk_name = list(kwargs.keys())[0]
        pk = kwargs[pk_name]

        if not pk:
            return

        model = cls.query.filter_by(**{pk_name: pk}).first()
        if model is None:
            model = cls()
            model.update(**kwargs)
            db.session.add(model)
        else:
            model.update(**kwargs)

        return model

    @classmethod
    def from_csv(
            cls,
            path: str = None,
            separator: str = ';',
            newline: str = '\n',
            encoding: str = 'utf8',
            remove_missing: bool = False
    ):
        """Load settings from CSV file.

        :param path: Path to csv file.
        :param separator: Cell separator character.
        :param newline: Line separator character.
        :param encoding: Encoding of CSV file.
        :param remove_missing: Delete entries missing from csv
        """
        if path is None:
            path = f'data/import/{getattr(cls, "__tablename__")}.csv'

        file_data = cls.load_csv(path, separator, newline, encoding)
        cls.load_data(file_data, remove_missing)

    @classmethod
    def load_data(cls, data: typing.Generator[dict, None, None], remove_missing: bool = False):
        updated = set()
        for model_data in data:
            model = cls.update_or_create(**model_data)
            if model and remove_missing:
                updated.add(int(model.id))

        if remove_missing:
            for m in cls.query:
                if int(m.id) not in updated:
                    db.session.delete(m)

        db.session.commit()


def ordered_mixin(container_class, backref: str):
    class Mixin:
        order_number = sa.Column(sa.Integer, index=True)

        @declared_attr
        def container_id(cls):
            return db.Column(db.Integer, db.ForeignKey(container_class.id), index=True)

        @declared_attr
        def container(cls):
            return db.relationship(
                container_class,
                backref=(db.backref(backref,
                                    lazy='dynamic',
                                    cascade='delete, delete-orphan',
                                    order_by=cls.order_number)))

        @classmethod
        def get_next_order_number(cls, container: container_class):

            last = db.session.query(sa.func.max(cls.order_number))\
                .filter(cls.container == container).first()[0]
            return (last or 0) + 1

        def set_order(self, new: int = None):
            cls = type(self)
            original = self.order_number

            if new is None:
                # Set as last
                self.order_number = cls.get_next_order_number(self.container)

            elif original is None:
                # Insert to new and push everything after by 1
                for item in db.session.query(cls)\
                        .filter(cls.container == self.container)\
                        .filter(cls.order_number >= new):
                    if item != self:
                        item.order_number -= 1

            elif original < new:
                # Pull everything between original and new by one
                for item in db.session.query(cls)\
                        .filter(cls.container == self.container)\
                        .filter(cls.order_number > original)\
                        .filter(cls.order_number <= new):
                    if item != self:
                        item.order_number -= 1

            elif original > new:
                # Push everything between original and new by one
                for item in db.session.query(cls)\
                        .filter(cls.container == self.container)\
                        .filter(cls.order_number < original)\
                        .filter(cls.order_number >= new):
                    if item != self:
                        item.order_number += 1

    return Mixin


db = SQLAlchemy(
    model_class=BaseModel,
    metadata=sa.MetaData(
        naming_convention={
            "ix": 'ix_%(column_0_label)s',
            "uq": "uq_%(table_name)s_%(column_0_name)s",
            "ck": "ck_%(table_name)s_%(column_0_name)s",
            "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
            "pk": "pk_%(table_name)s"
        }))

def name_column(
        length: int = 80,
        nullable: bool = False,
        unique: bool = True,
        index: bool = True):
    return db.Column(
        db.String(length),
        nullable=nullable,
        unique=unique,
        index=index)


class Role(db.Model, RoleMixin):
    name = name_column()
    description = db.Column(db.Text)

    def __repr__(self) -> str:
        """String representation of role."""
        return self.name


class User(db.Model, UserMixin):
    username = db.Column(db.String(16), unique=True, nullable=False, index=True)
    email = db.Column(db.String(255), unique=True, index=True)
    password = db.Column(db.String(255))
    language = db.Column(db.String(8), default='hu')

    active = db.Column(db.Boolean, default=True)
    registered_at = db.Column(db.DateTime, default=dt.datetime.utcnow)

    roles = db.relationship(
        "Role",
        secondary=db.Table(
            'user_role',
            db.Column('user_id', db.Integer,
                      db.ForeignKey('user.id'), primary_key=True),
            db.Column('role_id', db.Integer,
                      db.ForeignKey('role.id'), primary_key=True)
        ),
        backref=db.backref("users", lazy="dynamic")
    )

    def __repr__(self) -> str:
        """String representation of user."""
        return self.username

    def update(self, **kwargs):
        for (k, v) in kwargs.items():
            if isinstance(v, str) and not v:
                continue
            if k == 'password':
                self.password = hash_password(v)
            elif not hasattr(self, k) and Role.query.filter_by(name=k).first():
                self.add_roles(k)
            else:
                setattr(self, k, v)

    @property
    def is_active(self) -> bool:
        return self.active

    def has_role(self, role: typing.Union[str, Role]) -> bool:
        """Returns `True` if the user identifies with the specified role.

        :param role: A role name or `Role` instance"""
        if super().has_role('admin'):
            return True
        else:
            return super().has_role(role)

    def has_any_role(self, *roles: typing.Union[str, Role]) -> bool:
        """Returns if user has any of the given roles.

        Returns True if user has the `admin` role."""
        if self.has_role('admin'):
            return True

        for role in roles:
            if self.has_role(role):
                return True

        return False

    def has_all_roles(self, *roles: typing.Union[str, Role]) -> bool:
        """Returns if user has all of the given roles.

        Returns True if user has the `admin` role."""
        if self.has_role('admin'):
            return True

        for role in roles:
            if not self.has_role(role):
                return False

        return True

    def add_roles(self, *roles: typing.Union[str, Role]):
        """Adds role to user."""
        for role in roles:
            if self.has_role(role):
                continue

            if isinstance(role, str):
                role_obj = Role.query.filter_by(name=role).first()
                if role_obj is None:
                    raise ValueError(f'Undefined role: {role}')
            else:
                role_obj = role

            self.roles.append(role_obj)

    def verify_password(self, password: str) -> bool:
        """Checks if given password is the same as the stored one.

        :param password: Password to check.
        :return: True if the stored password was provided.

        :raise ValueError: If password is not set.
        """
        if self.password is None:
            raise ValueError('Password is not set.')

        return verify_password(password, self.password)

    def set_password(self, password: str) -> None:
        """Stores new password in database."""
        self.password = hash_password(password)


class Quiz(db.Model):
    name = name_column(unique=False)
    start_time = db.Column(db.DateTime, default=dt.datetime.utcnow, index=True)
    end_time = db.Column(db.DateTime, index=True)
    password = db.Column(db.String(255))
    last_updated = db.Column(db.DateTime)

    hosts = db.relationship(
        "User",
        secondary=db.Table(
            'host',
            db.Column('user_id', db.Integer,
                      db.ForeignKey('user.id'), primary_key=True),
            db.Column('quiz_id', db.Integer,
                      db.ForeignKey('quiz.id'), primary_key=True)
        ),
        backref=db.backref("quizzes", lazy="dynamic"))

    def __repr__(self) -> str:
        return self.name

    def points(self, user: User) -> float:
        return sum([ans.points for ans in user.answers.join(Section, Quiz).filter(Quiz.id == self.id)])

    def data(
            self,
            user: User,
            cached_content: list = None,
            cached_answers: list = None) -> dict:
        return {
            'id': self.id,
            'name': self.name,
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'sections': [section.as_dict(user, cached_content=cached_content, cached_answers=cached_answers)
                         for section in self.sections],
            'points': sum([section.points(user) for section in self.sections if section.closed])
        }


class Section(db.Model, ordered_mixin(Quiz, 'sections')):
    name = name_column(unique=False)
    open = db.Column(db.Boolean, default=False)
    closed = db.Column(db.Boolean, default=False)

    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), index=True)
    user = db.relationship(
        User,
        backref=(db.backref('sections',
                            lazy='dynamic',
                            cascade='delete, delete-orphan')))

    def __repr__(self) -> str:
        return self.name

    def points(self, user: User) -> float:
        if user.id == self.user_id:
            users = set()
            for answer in Answer.query.join(Question).filter(Question.container_id == self.id):
                if answer.user_id != user.id:
                    users.add(answer.user)

            return max([self.points(u) for u in users]) if users else 0

        return sum([ans.points for ans in user.answers.join(Question, Section).filter(Section.id == self.id)])

    @property
    def average(self):
        users = set()
        for answer in Answer.query.join(Question).filter(Question.container_id == self.id):
            if answer.user_id != answer.question.container.user_id:
                users.add(answer.user)

        return sum([self.points(u) for u in users]) / (len(users) or 1)

    def as_dict(
            self,
            user: User,
            cached_content: list = None,
            cached_answers: list = None) -> dict:
        is_host = self.user_id == user.id
        return {
            'id': self.id,
            'name': self.name,
            'order_number': self.order_number,
            'user': self.user.username,
            'open': True,
            'closed': self.closed,
            'questions': [question.as_dict(user, cached_content=cached_content, cached_answers=cached_answers)
                          for question in self.questions if is_host or question.open],
            'points': self.points(user) \
                if self.closed and self.questions.filter_by(open=False).first() is None \
                else None,
            'average': self.average if self.closed or is_host else None,
            'host': is_host
        }


class Question(db.Model, ordered_mixin(Section, 'questions')):
    content = db.deferred(db.Column(db.Text(12800)))
    answer_content = db.deferred(db.Column(db.Text(12800)))
    show_values = db.Column(db.Boolean, default=False)
    max_answers = db.Column(db.Integer, default=1)
    base_points = db.Column(db.Integer, default=0)
    bonus = db.Column(db.Boolean, default=False)
    open = db.Column(db.Boolean, default=False)
    closed = db.Column(db.Boolean, default=False)

    likes = db.relationship(
        "User",
        secondary=db.Table(
            'question_like',
            db.Column('user_id', db.Integer,
                      db.ForeignKey('user.id'), primary_key=True),
            db.Column('question_id', db.Integer,
                      db.ForeignKey('question.id'), primary_key=True)
        ),
        lazy='dynamic',
        backref=db.backref("liked_questions", lazy="dynamic"))

    def points(self, user: User) -> float:
        return sum([ans.points for ans in user.answers.filter_by(question_id=self.id)])

    @property
    def average(self):
        users = set()
        for answer in self.answers:
            if answer.user_id != answer.question.container.user_id:
                users.add(answer.user)

        return sum([self.points(u) for u in users]) / (len(users) or 1)

    def allowed(self, user: User) -> bool:
        if self.closed:
            return False

        if self.bonus:
            ans = Answer.query.join(Question)\
                .filter(Question.container_id == self.container_id)\
                .filter(Question.bonus == True)\
                .filter(Question.id != self.id)\
                .filter(Answer.user_id == user.id)\
                .first()

            if ans is not None:
                return False

        return True

    def as_dict(
            self,
            user: User,
            cached_content: list = None,
            cached_answers: list = None) -> dict:
        return {
            'id': self.id,
            'order_number': self.order_number,
            'content': self.content if self.id not in cached_content and self.open else None,
            'answer_content': self.answer_content if self.container.closed and self.id not in cached_answers else None,
            'max_answers': self.max_answers,
            'base_points': self.base_points,
            'open': self.open,
            'closed': not self.allowed(user),
            'likes': self.likes.count() or 0,
            'liked': bool(user in self.likes),
            'values': [value.text for value in self.values] if self.show_values else None,
            'answers': {answer.value: (self.container.closed or self.closed) and answer.points
                        for answer in self.answers.filter_by(user_id=user.id).all()},
            'points': self.points(user) if self.container.closed else None,
            'average': self.average if self.closed or self.container.user_id == user.id  else None,
            'correct': [value.text for value in self.values if value.points > 0] if self.container.closed else [],
            'host': self.container.user_id == user.id,
            'bonus': self.bonus}

    def duplicate(self):
        question = Question(
            content=self.content,
            show_values=self.show_values,
            max_answers=self.max_answers,
            base_points=self.base_points,
            bonus=self.bonus,
            container_id=self.container_id,
            order_number=Question.get_next_order_number(self.container)
        )
        db.session.add(question)
        for v in self.values:
            db.session.add(Value(
                text=v.text,
                allowed_misses=v.allowed_misses,
                points=v.points,
                order_number=v.order_number,
                question=question))

    def __repr__(self) -> str:
        return f"{self.container.container or ''} / {self.container} / {self.order_number}."


class Value(db.Model):
    text = db.Column(db.String(255), nullable=False)
    allowed_misses = db.Column(db.Integer, default=0)
    points = db.Column(db.Float, default=1.0)
    order_number = db.Column(db.Integer, index=True)

    question_id = db.Column(db.Integer, db.ForeignKey('question.id'), index=True, nullable=False)
    question = db.relationship(
        Question,
        backref=(db.backref('values',
                            lazy='dynamic',
                            order_by='Value.order_number',
                            cascade='delete, delete-orphan')))


class Answer(db.Model):
    value = db.Column(db.String(255))
    timestamp = db.Column(db.DateTime, default=dt.datetime.utcnow)

    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), index=True)
    user = db.relationship(
        User,
        backref=(db.backref('answers',
                            lazy='dynamic',
                            cascade='delete, delete-orphan')))

    question_id = db.Column(db.Integer, db.ForeignKey('question.id'), index=True)
    question = db.relationship(
        Question,
        backref=(db.backref('answers',
                            lazy='dynamic',
                            cascade='delete, delete-orphan')))

    @property
    def points(self) -> float:
        for value in self.question.values.filter(Value.points <= 0):
            if value.allowed_misses:
                d = str_distance(value.text, self.value)
                if d < value.allowed_misses:
                    return value.points or 0
            elif value.text == self.value:
                return value.points

        for value in self.question.values.filter(Value.points > 0):
            val = value.text.strip().lower()\
                .replace('the ', '')\
                .replace('a ', '')\
                .replace('az ', '')\
                .replace(' ', '')\
                .replace('-', '')
            text = self.value.strip().lower()\
                .replace('the ', '')\
                .replace('a ', '')\
                .replace('az ', '')\
                .replace(' ', '')\
                .replace('-', '')
            if value.allowed_misses:
                d = str_distance(val, text)
                if d < value.allowed_misses:
                    return value.points or 0
            elif val == text:
                return value.points

        return self.question.base_points
