import datetime as dt
import time as tm

from flask import current_app, has_app_context, abort, request, redirect, flash, jsonify, url_for
from flask_admin import Admin, expose, AdminIndexView
from flask_admin.contrib.sqla import ModelView as SQLAlchemyModelView
from flask_admin.contrib.sqla.filters import EnumEqualFilter
from flask_admin.contrib.sqla.form import get_form
from flask_admin.model.form import create_editable_list_form
from flask_babelex import gettext as _, lazy_gettext as _l
from flask_security import current_user, login_required
import sqlalchemy as sa
import wtforms as wtf

import model as md
from form import CreateSectionForm, TEMPLATE_FORMS


class IndexView(AdminIndexView):
    api_updates = {}

    @expose('/')
    def index(self, page: int = 1):
        per_page = current_app.config.get('PER_PAGE', 20)
        hosted = [q.id for q in current_user.quizzes] if current_user.is_authenticated else []
        now = dt.datetime.utcnow()

        quizzes = md.Quiz.query\
            .filter(sa.or_(
                sa.and_(
                    md.Quiz.start_time.isnot(None),
                    md.Quiz.start_time < now),
                md.Quiz.id.in_(hosted)))\
            .order_by(md.Quiz.start_time.desc())\
            .paginate(page, per_page, error_out=False)

        return self.render('index.html', quizzes=quizzes, now=now)

    @expose('/quiz/<int:quiz_id>/')
    def quiz(self, quiz_id: int):
        quiz = md.Quiz.query.get(quiz_id)
        if quiz is None:
            return abort(404)

        if current_user.is_anonymous:
            return abort(403)

        return self.render('quiz.html', quiz=quiz)

    @expose('/quiz/<int:quiz_id>/static')
    def quiz_static(self, quiz_id: int):
        quiz = md.Quiz.query.get(quiz_id)
        if quiz is None:
            return abort(404)

        return self.render('quiz_static.html', quiz=quiz)

    @expose('/quiz/<int:quiz_id>/edit')
    def edit_quiz(self, quiz_id: int):
        quiz = md.Quiz.query.get(quiz_id)
        if quiz is None:
            return abort(404)

        if current_user.is_anonymous:
            return abort(403)

        return self.render('editor/quiz.html', quiz=quiz)

    @expose('/add_section', methods=['GET', 'POST'])
    @expose('/quiz/<int:quiz_id>/add_section', methods=['GET', 'POST'])
    def add_section(self, quiz_id: int = None):
        template = request.args.get('template', None)
        form = TEMPLATE_FORMS.get(template, CreateSectionForm)()

        if isinstance(form, CreateSectionForm):
            form.existing.choices = [(s.id, s.name) for s in current_user.sections.filter_by(container_id=None)]
            if request.method == 'POST' and form.validate_on_submit():
                if form.load_template.data:
                    return redirect(url_for('admin.add_section', quiz_id=quiz_id, template=form.template.data))
                elif form.load_existing.data:
                    section = md.Section.query.get(form.existing.data)
                    section.container_id = quiz_id
                    md.db.session.commit()
                    return redirect(url_for('section.edit_view', id=section.id, url='/'))
            else:
                if quiz_id is None:
                    del(form.existing)
                    del(form.load_existing)
                return self.render('editor/template.html', form=form)

        else:
            if request.method == 'POST' and form.validate_on_submit():
                if form.submit.data:
                    quiz = md.Quiz.query.get(quiz_id or 0)
                    section = form.create(quiz)
                    md.db.session.commit()
                    return redirect(url_for('section.edit_view', id=section.id, url='/'))

            return self.render('editor/template.html', form=form)


    @expose('/api/quiz/<int:quiz_id>/', methods=['GET', 'POST'])
    def quiz_data(self, quiz_id: int):
        force = request.args.get('force', False)
        cached_content = [int(x) if x else 0 for x in request.args.get('cached_content', '0').split(',')]
        cached_answers = [int(x) if x else 0 for x in request.args.get('cached_answers', '0').split(',')]

        quiz = md.Quiz.query.get(quiz_id)
        if quiz is None:
            return abort(404)

        if current_user.is_anonymous:
            return abort(403)

        if force or self.api_updates.get((current_user.id, quiz_id), dt.datetime(1970, 1, 1)) < quiz.last_updated:
            self.api_updates[(current_user.id, quiz_id)] = dt.datetime.utcnow()
            resp = quiz.data(current_user, cached_content=cached_content, cached_answers=cached_answers)
            return jsonify(resp)

        return jsonify(None)

    @expose('/api/quiz/<int:quiz_id>/join', methods=['GET', 'POST'])
    def join(self, quiz_id: int):
        password = request.json.get('password', None) if request.json else request.values.get('password', None)
        quiz = md.Quiz.query.get(quiz_id)
        if quiz is None:
            return abort(404)

        if current_user.is_anonymous or quiz.password != password:
            return abort(403)

        quiz.hosts.append(current_user)
        md.db.session.commit()

        return jsonify(None)

    @expose('/api/questions/<int:question_id>/like', methods=['POST'])
    def like(self, question_id: int):
        question: md.Question = md.Question.query.get(question_id)
        if question is None:
            return abort(404)

        if current_user.is_anonymous:
            return abort(403)

        if current_user in question.likes:
            question.likes.remove(current_user)
        else:
            question.likes.append(current_user)
        question.container.container.last_updated = dt.datetime.utcnow()
        md.db.session.commit()
        return jsonify(None)

    @expose('/api/sections/<int:section_id>/open', methods=['POST'])
    def open_section(self, section_id: int):
        section: md.Section = md.Section.query.get(section_id)
        if section is None:
            return abort(404)

        if not (current_user.is_authenticated
                and (current_user.id == section.user_id or current_user.has_role('admin'))):
            return abort(403)

        section.open = not section.open
        section.container.last_updated = dt.datetime.utcnow()
        md.db.session.commit()
        return jsonify(None)

    @expose('/api/sections/<int:section_id>/close', methods=['POST'])
    def close_section(self, section_id: int):
        section: md.Section = md.Section.query.get(section_id)
        if section is None:
            return abort(404)

        if not (current_user.is_authenticated
                and (current_user.id == section.user_id or current_user.has_role('admin'))):
            return abort(403)

        section.closed = not section.closed
        if section.closed:
            for question in section.questions:
                question.open = False
                question.closed = True
        section.container.last_updated = dt.datetime.utcnow()
        md.db.session.commit()
        return jsonify(None)

    @expose('/api/questions/<int:question_id>/open', methods=['POST'])
    def open_question(self, question_id: int):
        question: md.Question = md.Question.query.get(question_id)
        if question is None:
            return abort(404)

        if not (current_user.is_authenticated
                and (current_user.id == question.container.user_id or current_user.has_role('admin'))):
            return abort(403)

        question.open = not question.open
        question.container.container.last_updated = dt.datetime.utcnow()
        md.db.session.commit()
        return jsonify(None)

    @expose('/api/questions/<int:question_id>/close', methods=['POST'])
    def close_question(self, question_id: int):
        question: md.Question = md.Question.query.get(question_id)
        if question is None:
            return abort(404)

        if not (current_user.is_authenticated
                and (current_user.id == question.container.user_id or current_user.has_role('admin'))):
            return abort(403)

        question.closed = not question.closed
        question.container.container.last_updated = dt.datetime.utcnow()
        md.db.session.commit()
        return jsonify(None)

    @expose('/api/questions/<int:question_id>/answer', methods=['POST'])
    def set_answer(self, question_id: int):
        question: md.Question = md.Question.query.get(question_id)
        if question is None:
            return abort(404)

        if current_user.is_anonymous:
            return abort(403)

        value = request.json.get('value', None) if request.json else request.values.get('value', None)

        if value:
            md.db.session.add(md.Answer(
                value=value,
                user_id=current_user.id,
                question_id=question.id))
            md.db.session.commit()

        return jsonify(None)

    @expose('/api/questions/<int:question_id>/clear', methods=['POST'])
    def clear_answers(self, question_id: int):
        question: md.Question = md.Question.query.get(question_id)
        if question is None:
            return abort(404)

        if current_user.is_anonymous:
            return abort(403)

        for answer in question.answers.filter_by(user_id=current_user.id):
            md.db.session.delete(answer)

        md.db.session.commit()
        return jsonify(None)


admin = Admin(
    name='DIY Quiz',
    template_mode='bootstrap3',
    index_view=IndexView(
        url='/'
    )
)


def add_view(name=None, category=None, model_class=None):
    def wrap(cls):
        if model_class is None:
            view = cls(
                name=name,
                category=category)
        else:
            view = cls(
                model_class,
                md.db.session,
                name=name,
                category=category
            )
        admin.add_view(view)

        return cls

    return wrap


def query_filter(model_class, label: str = None, flt=None):
    if label is None:
        label = _l(model_class.__name__)

    if flt:
        qry = model_class.query.filter(flt)
    else:
        qry = model_class.query
    return EnumEqualFilter(model_class.id, label,
                           options=[(x.id, str(x)) for x in qry.all()])


class ModelView(SQLAlchemyModelView):
    can_set_page_size = True
    page_size = 20

    columns = {}

    can_export = True
    export_types = ['xlsx', 'csv', 'json', 'dbf']

    column_extra_fields = {}

    def is_accessible(self) -> bool:
        return current_user.is_authenticated

    @property
    def column_list(self) -> tuple:
        return tuple(self.columns.keys()) or []

    @property
    def column_labels(self) -> dict:
        return self.columns or {}

    def scaffold_list_form(self, widget=None, validators=None):
        """
            Create form for the `index_view` using only the columns from
            `self.column_editable_list`.

            :param widget:
                WTForms widget class. Defaults to `XEditableWidget`.
            :param validators:
                `form_args` dict with only validators
                {'name': {'validators': [required()]}}
        """
        converter = self.model_form_converter(self.session, self)
        form_class = get_form(self.model, converter,
                              base_class=self.form_base_class,
                              only=self.column_editable_list,
                              field_args=validators,
                              extra_fields=self.column_extra_fields)

        # if widget is None:
        #    widget = XEditableWidgetWithDateTime()

        return create_editable_list_form(self.form_base_class, form_class,
                                         widget)

    @classmethod
    def add_view(cls):
        admin.add_view(cls(
            cls.model_class,
            md.db.session,
            name=cls.name,
            category=cls.category
        ))

    @property
    def _column_filters(self):
        return []

    @property
    def column_filters(self):
        if has_app_context():
            return self._column_filters
        else:
            return []

    @property
    def column_type_formatters(self) -> dict:
        data = super().column_type_formatters
        data.update({
            dt.datetime:
                lambda view, value: value.strftime('%Y.%m.%d %H:%M:%S'),
            float:
                lambda view, value: value if value % 1 else int(value)
        })
        return data

    def get_empty_list_message(self):
        """Returns the message shown if there are no records to show."""
        return _l('There are no items in the table.')


@add_view(_l('Quizzes'), _l('Editor'), md.Quiz)
class QuizView(ModelView):
    columns = {
        'hosts': _l('Hosts'),
        'name': _l('Name'),
        'start_time': _l('Start Time'),
        'end_time': _l('End Time'),
        'password': _l('Password')
    }

    form_excluded_columns = ['sections']
    edit_template = 'editor/quiz.html'

    def get_query(self):
        if not current_user.has_role('admin'):
            return current_user.quizzes

        return md.Quiz.query

    def get_count_query(self):
        ids = [q.id for q in current_user.quizzes]

        if not current_user.has_role('admin'):
            return md.db.session.query(sa.func.count(md.Quiz.id)).filter(md.Quiz.id.in_(ids))

        return md.db.session.query(sa.func.count(md.Quiz.id))

    def check_access(self):
        if current_user.has_role('admin'):
            return

        quiz = md.Quiz.query.get(request.args.get('id'))
        if quiz and current_user not in quiz.hosts:
            return abort(403)

    @expose('/edit/', methods=('GET', 'POST'))
    def edit_view(self):
        return self.check_access() or super().edit_view()

    @expose('/delete/', methods=('POST',))
    def delete_view(self):
        return self.check_access() or super().delete_view()

    def on_model_change(self, form, model, is_created):
        if is_created and current_user not in model.hosts:
            model.hosts.append(current_user)
        md.db.session.commit()


@add_view(_l('Sections'), _l('Editor'), md.Section)
class SectionView(ModelView):
    columns = {
        'user': _l('User'),
        'container': _l('Quiz'),
        'order_number': _l('Order Number'),
        'name': _l('Name'),
        'closed': _l('Closed')
    }
    form_excluded_columns = ['questions', 'user', 'open', 'closed', 'container']
    column_editable_list = ['order_number', 'name', 'closed']
    edit_template = 'editor/section.html'

    def check_access(self):
        if current_user.has_role('admin'):
            return

        section = md.Section.query.get(request.args.get('id'))
        if section and section.user_id != current_user.id:
            return abort(403)

        quiz = md.Quiz.query.get(request.args.get('quiz_id'))
        if quiz and current_user not in quiz.hosts:
            return abort(403)

    @expose('/create/', methods=('GET', 'POST'))
    def create_view(self):
        return self.check_access() or super().create_view()

    @expose('/edit/', methods=('GET', 'POST'))
    def edit_view(self):
        return self.check_access() or super().edit_view()

    @expose('/delete/', methods=('POST',))
    def delete_view(self):
        return self.check_access() or super().delete_view()

    def create_form(self, obj=None):
        form = super().create_form(obj)
        container_id = request.args.get('quiz_id', None)
        if container_id:
            form.order_number.data = md.Section.get_next_order_number(md.Quiz.query.get(container_id))
        return form

    def on_model_change(self, form, model, is_created):
        container_id = request.args.get('quiz_id', None)
        if container_id:
            model.container_id = container_id
        if is_created and model.order_number is None:
            model.set_order()
        if model.user is None:
            model.user = current_user
        md.db.session.commit()

    def get_query(self):
        query = md.db.session.query(md.Section)\
            .order_by(md.Section.container_id, md.Section.order_number)

        if not current_user.has_role('admin'):
            query = query.filter_by(user_id=current_user.id)

        return query

    def get_count_query(self):
        query = md.db.session.query(sa.func.count(md.Section.id))\
            .order_by(md.Section.container_id, md.Section.order_number)

        if not current_user.has_role('admin'):
            query = query.filter_by(user_id=current_user.id)

        return query


@add_view(_l('Questions'), _l('Editor'), md.Question)
class QuestionView(ModelView):
    columns = {
        'container': _l('Section'),
        'order_number': _l('Order Number'),
        'content': _l('Content'),
        'answer_content': _l('Answer Content'),
        'show_values': _l('Show Values'),
        'max_answers': _l('Max Answers'),
        'base_points': _l('Base Points'),
        'bonus': _l('Bonus'),
        'open': _l('Visible'),
        'closed': _l('Closed')
    }

    form_excluded_columns = ['container', 'likes', 'values', 'attachments', 'answers', 'open', 'closed']
    column_exclude_list = ['content', 'answer_content']
    column_editable_list = ['open', 'closed']

    def get_query(self):
        query = md.db.session.query(md.Question)\
            .join(md.Section)\
            .order_by(md.Section.container_id, md.Section.order_number, md.Question.order_number)

        if not current_user.has_role('admin'):
            query = query.filter(md.Section.user_id == current_user.id)

        return query

    def get_count_query(self):
        query = md.db.session.query(sa.func.count(md.Question.id))\
            .join(md.Section)\
            .order_by(md.Section.container_id, md.Section.order_number, md.Question.order_number)

        if not current_user.has_role('admin'):
            query = query.filter(md.Section.user_id == current_user.id)

        return query

    def check_access(self):
        if current_user.has_role('admin'):
            return

        question = md.Question.query.get(request.args.get('id'))
        if question and question.container.user_id != current_user.id:
            return abort(403)

        section = md.Section.query.get(request.args.get('section_id'))
        if section and section.user_id != current_user.id:
            return abort(403)

    @expose('/create/', methods=('GET', 'POST'))
    def create_view(self):
        return self.check_access() or super().create_view()

    @expose('/edit/', methods=('GET', 'POST'))
    def edit_view(self):
        return self.check_access() or super().edit_view()

    @expose('/delete/', methods=('POST',))
    def delete_view(self):
        return self.check_access() or super().delete_view()

    @expose('/duplicate/', methods=('POST',))
    def duplicate(self):
        question = md.Question.query.get(request.values.get('id', 0))
        if question is None:
            return abort(404)

        url = request.values.get('url', request.referrer)

        err = self.check_access()
        if err:
            return err

        question.duplicate()
        md.db.session.commit()

        return redirect(url)

    def create_form(self, obj=None):
        form = super().create_form(obj)
        container_id = request.args.get('section_id', None)
        if container_id:
            form.order_number.data = md.Question.get_next_order_number(md.Section.query.get(container_id))
        return form

    def on_model_change(self, form, model, is_created):
        container_id = request.args.get('section_id', None)
        if container_id:
            model.container_id = container_id
        if is_created and model.order_number is None:
            model.set_order()
        md.db.session.commit()


@add_view(_l('Values'), _l('Editor'), md.Value)
class ValueView(ModelView):
    columns = {
        'question.container.container': _l('Quiz'),
        'question.container': _l('Section'),
        'question.order_number': _l('Question Number'),
        'order_number': _l('Order Number'),
        'text': _l('Text'),
        'allowed_misses': _l('Allowed Misses'),
        'points': _l('Points')
    }
    form_excluded_columns = ['question']

    def get_query(self):
        query = md.db.session.query(md.Value)\
            .join(md.Question).join(md.Section)\
            .order_by(md.Section.container_id, md.Section.order_number, md.Question.order_number, md.Value.order_number)

        if not current_user.has_role('admin'):
            query = query.filter(md.Section.user_id == current_user.id)

        return query

    def get_count_query(self):
        query = md.db.session.query(sa.func.count(md.Value.id))\
            .join(md.Question).join(md.Section)\
            .order_by(md.Section.container_id, md.Section.order_number, md.Question.order_number, md.Value.order_number)

        if not current_user.has_role('admin'):
            query = query.filter(md.Section.user_id == current_user.id)

        return query

    def check_access(self):
        if current_user.has_role('admin'):
            return

        value = md.Value.query.get(request.args.get('id'))
        if value and value.question.container.user_id != current_user.id:
            return abort(403)

        question = md.Question.query.get(request.args.get('question_id'))
        if question and question.container.user_id != current_user.id:
            return abort(403)

    @expose('/create/', methods=('GET', 'POST'))
    def create_view(self):
        return self.check_access() or super().create_view()

    @expose('/edit/', methods=('GET', 'POST'))
    def edit_view(self):
        return self.check_access() or super().edit_view()

    @expose('/delete/', methods=('POST',))
    def delete_view(self):
        return self.check_access() or super().delete_view()


    def on_model_change(self, form, model, is_created):
        question_id = request.args.get('question_id', None)
        if question_id:
            model.question_id = question_id
        md.db.session.commit()


@add_view(_l('Answers'), _l('Editor'), md.Answer)
class AnswerView(ModelView):
    columns = {
        'question.container.container': _l('Quiz'),
        'question.container': _l('Section'),
        'question.order_number': _l('Question Number'),
        'user.username': _l('Username'),
        'value': _l('Answer'),
        'points': _l('Points')
    }
    column_filters = ['user.username']

    def can_create(self) -> bool:
        return current_user.has_role('admin')

    def can_edit(self) -> bool:
        return current_user.has_role('admin')

    def can_delete(self) -> bool:
        return current_user.has_role('admin')

    def get_query(self):
        query = md.db.session.query(md.Answer)\
            .join(md.Question).join(md.Section)\
            .order_by(md.Section.container_id, md.Section.order_number, md.Question.order_number)

        if not current_user.has_role('admin'):
            query = query.filter(md.Section.user_id == current_user.id)

        return query

    def get_count_query(self):
        query = md.db.session.query(sa.func.count(md.Answer.id))\
            .join(md.Question).join(md.Section)\
            .order_by(md.Section.container_id, md.Section.order_number, md.Question.order_number)

        if not current_user.has_role('admin'):
            query = query.filter(md.Section.user_id == current_user.id)

        return query


@add_view(_l('Users'), _l('Admin'), md.User)
class UserView(ModelView):
    def is_accessible(self) -> bool:
        return current_user.has_role('admin')

    columns = {
        'username': _l('Username'),
        'email': _l('E-mail'),
        'language': _l('Language'),
        'roles': _l('Roles'),
        'registered_at': _l('Registered At'),
        'active': _l('Active')
    }
    column_exclude_list = ['active', 'password']
    form_excluded_columns = ['password', 'registered_at', 'quizzes', 'sections', 'liked_questions', 'answers']
