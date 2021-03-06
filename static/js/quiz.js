const CONTENT_CACHE = {};
const ANSWER_CONTENT_CACHE = {};
var autoRefresh = true;

function renderQuestion(data) {
    var inputs = "";
    const sectionClosed = !!data.correct.length;

    if (data.content) {
        CONTENT_CACHE[data.id] = data.content
    }
    if (data.answer_content) {
        ANSWER_CONTENT_CACHE[data.id] = data.answer_content
    }

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

    var answersStr = Object.keys(data.answers).join(', ');
    if (answersStr.length > 20) {
        answersStr = answersStr.substring(0, 17) + '...'
    }

    return `
    <div id="question-${data.id}" class="jumbotron question">
        <h3>${data.order_number}. ${data.bonnus ? `<span class="glyphicon glyphicon-asterisk"></span> ` : ''}${data.points != null ? `<span class="section-points">${data.points}p</span>` : ''}</h3>
        <div class="question-content ${data.closed ? 'disabled' : 'enabled'}">
            ${data.text || ''}
            <br>
            ${CONTENT_CACHE[data.id] || ''}
            <br>
            ${sectionClosed ? ANSWER_CONTENT_CACHE[data.id] || '' : ''}
        </div>
        <div class="question-bar">
            <div class="btn-group" role="group">
                ${data.host ?  `
                <button type="button" class="btn btn-${data.open ? 'success' : 'default'}" onclick="openQuestion(${data.id})">
                    <span class="glyphicon glyphicon-eye-open"></span>   
                </button>
                <button type="button" class="btn btn-${data.closed ? 'danger' : 'default'}" onclick="closeQuestion(${data.id})">
                    <span class="glyphicon glyphicon-lock"></span>
                </button>` : 
                `<button type="button" class="btn btn-success ${sectionClosed || data.closed ? 'disabled' : ''}" ${sectionClosed || data.closed ? 'disabled' : ''} onclick="setAnswer(${data.id})">
                    <span class="glyphicon glyphicon-save"></span> ${data.answers ? answersStr : ''}  
                </button>`}
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
                <button type="button" class="btn btn-default" onclick="refreshQuestion(${data.id})">
                    <span class="glyphicon glyphicon-refresh"></span>   
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

    var rows = '';
    data.rankings.forEach(function (item) {
        rows += `<tr${item.id === data.user_id ? ' class="bg-primary"' : ''}>
            <td>${item.rank}</td>
            <td style="width: 100%">${item.id === data.user_id ? '<span class="glyphicon glyphicon-user"></span>' : ''} ${item.username}</td>
            <td class="text-right">${item.rank < 4 ? item.points : ''}</td>
        </tr>`
    })

    return `
    <h1 class="quiz-title">${data.name}</h1>
    ${sections}
    <div id="rankings" class="jumbotron">
        <table class="table">${rows}</table>
    </div>
    <div class="total-score">
        ${points}p
    </div>
    `
}

function update(repeat = false) {
    data = {'cached_content': Object.keys(CONTENT_CACHE).join(','), 'cached_answers': Object.keys(ANSWER_CONTENT_CACHE).join(',')}
    if (!repeat) {
        data.force = true
    }
    $.getJSON(`/api/quiz/${QUIZ_ID}/`, data, function(data) {
        if (data) {
            if (!repeat || autoRefresh) {
                $('#quiz').html(renderQuiz(data));
                /*$(".question-text, .question-radio").on('change', function(){
                    setAnswer($(this).attr('data-id'));
                });*/
                $('form').on('submit', (evt) => evt.preventDefault());
            }
        }
    }).always(function() {
        if (repeat && autoRefresh) {
            setTimeout(function() {update(true)}, 2000);
        }
    });
}

function setAutoRefresh(refreshing) {
    autoRefresh = refreshing;
    if (refreshing) {
        $('#auto-refresh span').addClass('glyphicon-pause').removeClass('glyphicon-play');
        update(true);
    } else {
        $('#auto-refresh span').removeClass('glyphicon-pause').addClass('glyphicon-play');
    }
}

function like(id) {
    $.post(`/api/questions/${id}/like`).done(function(data) {
        $(`#question-${data.id}`).replaceWith(renderQuestion(data));
        $('form').on('submit', (evt) => evt.preventDefault());
    });
    $(`#question-${id} button`).attr('disabled', true);
}

function openQuestion(id) {
    $.post(`/api/questions/${id}/open`).always(function() {update()});
    $(`#question-${id} button`).attr('disabled', true);
}

function closeQuestion(id) {
    $.post(`/api/questions/${id}/close`).always(function() {update()});
    $(`#question-${id} button`).attr('disabled', true);
}

function openSection(id) {
    $.post(`/api/sections/${id}/open`).always(function() {update()});
    $(`#section-${id} button`).attr('disabled', true);
}

function closeSection(id) {
    $.post(`/api/sections/${id}/close`).always(function() {update()});
    $(`#section-${id} button`).attr('disabled', true);
}

function setAnswer(id) {
    $.post(`/api/questions/${id}/clear`).always(function() {
        $(`.question-text[data-id=${id}]`).each(function (index, item) {
            $.post(`/api/questions/${id}/answer`, {value: $(item).val()}).done(function(data) {
                $(`#question-${data.id}`).replaceWith(renderQuestion(data));
                $('form').on('submit', (evt) => evt.preventDefault());
            })
        });
        $(`.question-radio[data-id=${id}]:checked`).each(function (index, item) {
            $.post(`/api/questions/${id}/answer`, {value: $(item).val()}).done(function(data) {
                $(`#question-${data.id}`).replaceWith(renderQuestion(data));
                $('form').on('submit', (evt) => evt.preventDefault());
            })
        });
        update();
    })
}

function refreshQuestion(id) {
    $.get(`/api/questions/${id}`).done(function(data) {
        $(`#question-${data.id}`).replaceWith(renderQuestion(data));
        $('form').on('submit', (evt) => evt.preventDefault());
    })
}


update(true);
update();