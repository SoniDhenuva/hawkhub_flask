(function () {
    const app = document.getElementById('club-finder-app');
    if (!app) {
        return;
    }

    const state = {
        layout: null,
        stepIndex: 0,
        answers: {
            selected_grade: null,
            selected_subjects: [],
            selected_activities: [],
            selected_vibes: []
        }
    };

    function hasSelection(step) {
        const value = state.answers[step.field];
        return Array.isArray(value) ? value.length > 0 : Boolean(value);
    }

    function isSelected(step, optionValue) {
        const value = state.answers[step.field];
        return Array.isArray(value) ? value.includes(optionValue) : value === optionValue;
    }

    function toggle(step, optionValue) {
        if (step.selection === 'single') {
            state.answers[step.field] = optionValue;
            return;
        }

        const existing = state.answers[step.field] || [];
        if (existing.includes(optionValue)) {
            state.answers[step.field] = existing.filter((entry) => entry !== optionValue);
            return;
        }

        state.answers[step.field] = [...existing, optionValue];
    }

    function summaryChips() {
        return Object.entries(state.answers).flatMap(([field, value]) => {
            if (!value) {
                return [];
            }
            if (Array.isArray(value)) {
                return value.map((entry) => `<span class="finder-chip">${entry}</span>`);
            }
            return [`<span class="finder-chip">${value}</span>`];
        });
    }

    function renderSummaryPanel() {
        const chips = summaryChips();
        if (chips.length === 0) {
            return '<p class="finder-help-text">Selections will collect here as the user moves through the flow.</p>';
        }
        return `<div class="finder-chip-list">${chips.join('')}</div>`;
    }

    function render() {
        if (!state.layout) {
            app.innerHTML = '<div class="finder-main"><p class="finder-help-text">Loading club finder...</p></div>';
            return;
        }

        const steps = state.layout.steps;
        const step = steps[state.stepIndex];
        const isLastStep = state.stepIndex === steps.length - 1;

        app.innerHTML = `
            <section class="finder-main">
                <div class="finder-kicker">${state.layout.badge}</div>
                <h1 class="finder-title">${state.layout.headline}</h1>
                <p class="finder-subtitle">${state.layout.subheadline}</p>

                <div class="finder-progress-row">
                    <div class="finder-progress-dots">
                        ${steps.map((item, index) => {
                            const classes = [
                                'finder-dot',
                                index === state.stepIndex ? 'is-active' : '',
                                index < state.stepIndex ? 'is-complete' : ''
                            ].filter(Boolean).join(' ');
                            const display = item.options[0] ? item.options[0].icon : String(index + 1).padStart(2, '0');
                            return `<div class="${classes}" title="${item.label}">${display}</div>`;
                        }).join('')}
                    </div>
                    <div class="finder-step-label">Step ${state.stepIndex + 1} of ${steps.length}</div>
                </div>

                <div class="finder-question-label">${step.label}</div>
                <h2 class="finder-question-title">${step.prompt}</h2>
                <p class="finder-question-copy">${step.description}</p>

                <div class="finder-options">
                    ${step.options.map((option) => `
                        <button class="finder-option ${isSelected(step, option.value) ? 'is-selected' : ''}" type="button" data-option-value="${option.value}">
                            <span class="finder-option-icon">${option.icon || '•'}</span>
                            <span class="finder-option-copy">
                                <strong>${option.label}</strong>
                                <span>${option.description || 'Select this option'}</span>
                            </span>
                        </button>
                    `).join('')}
                </div>

                <div class="finder-controls">
                    <button class="finder-button-ghost" type="button" id="finder-back" ${state.stepIndex === 0 ? 'disabled' : ''}>${state.layout.actions.back}</button>
                    <button class="finder-button" type="button" id="finder-next" ${hasSelection(step) ? '' : 'disabled'}>${isLastStep ? state.layout.actions.restart : state.layout.actions.next}</button>
                </div>
            </section>

            <aside class="finder-side">
                <section class="finder-meta-card">
                    <div class="finder-side-title">Current Inputs</div>
                    ${renderSummaryPanel()}
                </section>
                <section class="finder-results-card">
                    <div class="finder-side-title">Why This Is Different</div>
                    <p class="finder-summary-note">The page layout, step order, labels, and option text are loaded from a backend JSON file. You can swap the structure later without rewriting the page markup.</p>
                </section>
            </aside>
        `;

        app.querySelectorAll('[data-option-value]').forEach((button) => {
            button.addEventListener('click', function () {
                toggle(step, this.dataset.optionValue);
                render();
            });
        });

        const backButton = document.getElementById('finder-back');
        if (backButton) {
            backButton.addEventListener('click', function () {
                state.stepIndex = Math.max(0, state.stepIndex - 1);
                render();
            });
        }

        const nextButton = document.getElementById('finder-next');
        if (nextButton) {
            nextButton.addEventListener('click', function () {
                if (isLastStep) {
                    state.stepIndex = 0;
                    state.answers = {
                        selected_grade: null,
                        selected_subjects: [],
                        selected_activities: [],
                        selected_vibes: []
                    };
                } else {
                    state.stepIndex += 1;
                }
                render();
            });
        }
    }

    async function init() {
        try {
            const response = await fetch(app.dataset.layoutUrl, { credentials: 'include' });
            const data = await response.json();
            if (!response.ok) {
                throw new Error(data.error || 'Unable to load club finder layout');
            }
            state.layout = data;
            render();
        } catch (error) {
            app.innerHTML = `<div class="finder-main"><p class="finder-empty-state">${error.message}</p></div>`;
        }
    }

    init();
}());