from flask_babelex import gettext as _, lazy_gettext as _l
from flask_security import current_user
from flask_wtf import FlaskForm
import wtforms as wtf


import model as md


class GenericForm(FlaskForm):
    name = wtf.StringField(
        _l('Name'),
        validators=[wtf.validators.DataRequired()]
    )
    order_number = wtf.IntegerField(
        _l('Order Number'),
        validators=[wtf.validators.DataRequired()],
        default=1
    )
    number_of_questions = wtf.IntegerField(
        _l('Number of Questions'),
        validators=[wtf.validators.DataRequired()],
        default=10
    )
    submit = wtf.SubmitField(_l('Create Section'))

    def create(self, quiz: md.Quiz):
        section = md.Section(
            user_id=current_user.id,
            container=quiz,
            order_number=self.order_number.data,
            name=self.name.data
        )
        md.db.session.add(section)

        for i in range(self.number_of_questions.data):
            question = md.Question(
                content=_('Question %(num)s', num=i+1),
                order_number=i+1,
                container=section
            )
            md.db.session.add(question)
            md.db.session.add(md.Value(
                text=_('Answer'),
                question=question,
                allowed_misses=3,
                points=1
            ))

        return section


class MultipleChoiceForm(GenericForm):
    number_of_choices = wtf.IntegerField(
        _l('Number of Choices'),
        validators=[wtf.validators.DataRequired()],
        default=4
    )
    submit = wtf.SubmitField(_l('Create Section'))

    def create(self, quiz: md.Quiz):
        section = md.Section(
            user_id=current_user.id,
            container=quiz,
            order_number=self.order_number.data,
            name=self.name.data
        )
        md.db.session.add(section)

        for i in range(self.number_of_questions.data):
            question = md.Question(
                content=_('Question %(num)s', num=i+1),
                order_number=i+1,
                show_values=True,
                container=section
            )
            md.db.session.add(question)
            for j in range(self.number_of_choices.data):
                md.db.session.add(md.Value(
                    text=_('Answer'),
                    question=question,
                    order_number=j+1,
                    points=0
                ))

        return section


class ConnectionForm(GenericForm):
    connection = wtf.StringField(
        _l('Connection'),
        validators=[wtf.validators.DataRequired()]
    )
    opportunities = wtf.IntegerField(
        _l('Opportunities'),
        validators=[wtf.validators.DataRequired()],
        default=3
    )
    submit = wtf.SubmitField(_l('Create Section'))

    def create(self, quiz: md.Quiz):
        section = md.Section(
            user_id=current_user.id,
            container=quiz,
            order_number=self.order_number.data,
            name=self.name.data
        )
        md.db.session.add(section)

        order_number = 1

        for i in range(self.number_of_questions.data-1):
            question = md.Question(
                content=_('Question %(num)s', num=i+1),
                order_number=order_number,
                show_values=False,
                container=section
            )
            order_number += 1
            md.db.session.add(question)
            md.db.session.add(md.Value(
                text=_('Answer'),
                question=question,
                allowed_misses=3,
                points=1
            ))
            if i < self.opportunities.data:
                question = md.Question(
                    content=_('What is the connection? (+%(num)s/-1)', num=self.opportunities.data - i),
                    order_number=order_number,
                    show_values=False,
                    bonus=True,
                    container=section
                )
                order_number += 1
                md.db.session.add(question)
                for ans in self.connection.data.split(','):
                    text = ans.strip()
                    md.db.session.add(md.Value(
                        text=text,
                        question=question,
                        allowed_misses=int(len(text) / 4) + 1,
                        points=self.opportunities.data + 1 - i
                    ))

        question = md.Question(
            content=_('What is the connection?'),
            order_number=order_number,
            show_values=False,
            bonus=True,
            container=section
        )
        md.db.session.add(question)
        for ans in self.connection.data.split(','):
            text = ans.strip()
            md.db.session.add(md.Value(
                text=text,
                question=question,
                allowed_misses=int(len(text) / 4) + 1,
                points=1
            ))


        return section


class WhoAmIForm(GenericForm):
    number_of_questions = wtf.IntegerField(
        _l('Number of Questions'),
        validators=[wtf.validators.DataRequired()],
        default=5
    )
    answer = wtf.StringField(
        _l('Answer'),
        validators=[wtf.validators.DataRequired()]
    )
    submit = wtf.SubmitField(_l('Create Section'))

    def create(self, quiz: md.Quiz):
        section = md.Section(
            user_id=current_user.id,
            container=quiz,
            order_number=self.order_number.data,
            name=self.name.data
        )
        md.db.session.add(section)

        for i in range(self.number_of_questions.data):
            question = md.Question(
                content=_('Statement %(num)s', num=i+1),
                order_number=i+1,
                show_values=False,
                bonus=True,
                container=section
            )
            md.db.session.add(question)
            for ans in self.answer.data.split(','):
                text = ans.strip()
                md.db.session.add(md.Value(
                    text=text,
                    question=question,
                    allowed_misses=int(len(text) / 4) + 1,
                    points=self.number_of_questions.data-i
                ))

        return section


TEMPLATE_FORMS = {
    'generic': GenericForm,
    'multiple': MultipleChoiceForm,
    'connection': ConnectionForm,
    'whoami': WhoAmIForm
}


class CreateSectionForm(FlaskForm):
    template = wtf.SelectField(
        _l('Template'),
        validators=[wtf.validators.Optional()],
        choices=(
            ('generic', _l('Generic')),
            ('multiple', _l('Multiple Choice')),
            ('connection', _l('Connection')),
            ('whoami', _l('Who am I?'))
        )
    )
    load_template = wtf.SubmitField(_l('Create from Template'))
    existing = wtf.SelectField(
        _l('Load Existing'),
        validators=[wtf.validators.Optional()],
        coerce=int
    )
    load_existing = wtf.SubmitField(_l('Load Existing'))
