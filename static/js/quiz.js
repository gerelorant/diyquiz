function renderQuestion(data) {
    var inputs = "";
    const sectionClosed = !!data.correct.length;

    if (data.values != null) {
        data.values.forEach(function (value) {
            const correct = data.correct.includes(value);
            inputs += `
                <div class="${correct ? 'has-success' : ((sectionClosed || data.closed) && Object.keys(data.answers).includes(value) ? 'has-error' : '')}">
                    <div class="radio">
                        <label>
                            <input type="radio" id="question-${data.id}-input" name="question-${data.id}-input" 
                                   value="${value}" data-id="${data.id}" ${Object.keys(data.answers).includes(value) ? 'checked' : ''}
                                   class="question-radio" ${sectionClosed || data.closed ? 'disabled' : ''}>
                            ${value}
                            <span class="glyphicon glyphicon-${Object.keys(data.answers).includes(value) ? (correct ? 'ok' : ((sectionClosed || data.closed) ? 'remove' : '')) : ''}"></span>
                            
                        </label>
                    </div>
                </div>`
        })
    } else {
        for (i = 0; i < data.max_answers; i++) {
            var answer = Object.keys(data.answers).length > i ? Object.keys(data.answers)[i] : "";
            const correct = (data.answers[answer] > 0);
            inputs += `
                <div class="form-group ${correct ? 'has-success' : (data.correct.length || data.closed ? 'has-error' : '')} has-feedback">
                    <input type="text" class="form-control${sectionClosed || data.closed ? ' disabled' : ''} question-text" 
                        id="question-${data.id}-input" name="question-${data.id}-input" data-id="${data.id}"
                        placeholder="${answer}" value="${answer}" ${sectionClosed || data.closed ? 'disabled' : ''}>
                    <span class="form-control-feedback">
                        ${correct ? data.answers[answer] : ''}
                        <span class="glyphicon glyphicon-${correct ? 'ok' : (data.correct.length || data.closed ? 'remove' : '')}"></span>
                    </span>
                </div>`
        }
    }

    var correctAnswers = '';
    data.correct.forEach(function(item) {
        correctAnswers += `<p>${item}</p>`
    });

    return `
    <div id="question-${data.id}" class="jumbotron question">
        <h3>${data.order_number}. ${data.bonnus ? `<span class="glyphicon glyphicon-asterisk"></span> ` : ''}${data.points != null ? `<span class="section-points">${data.points}p</span>` : ''}</h3>
        <div class="question-content ${data.closed ? 'disabled' : 'enabled'}">
            ${data.content || ''}
            <br>
            ${sectionClosed && data.answer_content ? data.answer_content : ''}
        </div>
        <div class="question-bar">
            <div class="btn-group" role="group">
                ${data.host ?  `
                <button type="button" class="btn btn-${data.open ? 'success' : 'default'}" onclick="openQuestion(${data.id})">
                    <span class="glyphicon glyphicon-eye-open"></span>   
                </button>
                <button type="button" class="btn btn-${data.closed ? 'danger' : 'default'}" onclick="closeQuestion(${data.id})">
                    <span class="glyphicon glyphicon-lock"></span>
                </button>` : ''}
                ${data.average != null ? `
                <button type="button" class="btn btn-default disabled">
                    <span class="glyphicon glyphicon-equalizer"></span> ${data.average}p</span>
                </button>` : ''}
                <button type="button" class="btn btn-default disabled">
                    <span class="glyphicon glyphicon-th-list"></span> ${data.max_answers}     
                </button>
                <button type="button" class="btn btn-default disabled">
                    <span class="glyphicon glyphicon-remove"></span> ${data.base_points}     
                </button>
                <button type="button" class="btn ${data.liked ? 'btn-primary' : 'btn-default'}" onclick="like(${data.id})">
                    <span class="glyphicon glyphicon-thumbs-up"></span> ${data.likes}
            </button>
            </div>  
        </div>
        <div class="answer-inputs">
            <form id="question-${data.id}-form" class="form" data-id="${data.id}">
                ${inputs}
            </form>
        </div>
        <div class="correct-answers">
              ${data.values == null ? correctAnswers : ''}  
        </div>
    </div>
    `
}

function renderSection(data) {
    var questions = "";
    data.questions.forEach(function (item) {
        questions += renderQuestion(item);
    });

    return `
    <div id="section-${data.id}">
        <h2>${data.order_number}. ${data.name} ${data.closed ? '<span class="glyphicon glyphicon-lock"></span>' : ''} ${data.points != null ? `<span class="section-points">${data.points}p</span>` : ''}</h2>
        
        <div class="section-bar">
            <div class="btn-group" role="group">
                ${data.host ?  `
                <button type="button" class="btn btn-${data.closed ? 'danger' : 'default'}" onclick="closeSection(${data.id})">
                    <span class="glyphicon glyphicon-lock"></span>
                </button>` : `
                <button type="button" class="btn btn-default disabled">
                    <span class="glyphicon glyphicon-user"></span> ${data.user} 
                </button>`}
                ${data.average != null ? `
                <button type="button" class="btn btn-default disabled">
                    <span class="glyphicon glyphicon-equalizer"></span> ${data.average}p</span>
                </button>` : ''}
            </div>  
        </div>
        ${questions}
    </div>
    `
}

function renderQuiz(data) {
    var sections = "";
    var points = 0;
    data.sections.forEach(function (item) {
        sections += renderSection(item);
        points = item.points ? points + item.points : points;
    });

    return `
    <h1 class="quiz-title">${data.name}</h1>
    ${sections}
    <div class="total-score">
        ${points}p
    </div>
    `
}

function update(repeat = false) {
    data = repeat ? {} : {'force': true};
    $.getJSON(`/api/quiz/${QUIZ_ID}/`, data, function(data) {
        if (data) {
            $('#quiz').html(renderQuiz(data));
            $(".question-text, .question-radio").on('change', function(){
                setAnswer($(this).attr('data-id'));
            });
            $('form').on('submit', (evt) => evt.preventDefault());
        }
    }).always(function() {
        if (repeat) {
            setTimeout(function() {update(true)}, 500);
        }
    });
}

function like(id) {
    $.post(`/api/questions/${id}/like`)
}

function openQuestion(id) {
    $.post(`/api/questions/${id}/open`)
}

function closeQuestion(id) {
    $.post(`/api/questions/${id}/close`)
}

function openSection(id) {
    $.post(`/api/sections/${id}/open`)
}

function closeSection(id) {
    $.post(`/api/sections/${id}/close`)
}

function setAnswer(id) {
    $.post(`/api/questions/${id}/clear`).always(function() {
        $(`.question-text[data-id=${id}]`).each(function (index, item) {
            $.post(`/api/questions/${id}/answer`, {value: $(item).val()})
        });
        $(`.question-radio[data-id=${id}]:checked`).each(function (index, item) {
            $.post(`/api/questions/${id}/answer`, {value: $(item).val()})
        });
    })
}


update(true);
update();