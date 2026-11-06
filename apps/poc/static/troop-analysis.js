/* Assessment component. Inject UI context and command dispatch; never mutate world state. */
const TroopAnalysis = {
  create({element: $, context, dispatch, toast, esc, clock}) {
    let unitId = null;
    let draft = null;
    let draftScope = null;
    let renderKey = null;

    function open() {
      const {state, selected} = context();
      const units = state.analysis?.units || [];
      if (!units.length) {
        toast('Troop assessment is unavailable. Refresh the page.');
        return;
      }
      unitId = units.some(unit => unit.id === selected) ? selected : units[0].id;
      draft = draftScope = renderKey = null;
      $('analysis-dialog').showModal();
      render();
    }

    function renderSummary(assessment, state, replay, godMode) {
      const summary = assessment.summary;
      const metrics = [
        [summary.reported_strength + ' / ' + summary.assigned_strength, 'reported troops'],
        [summary.available_formations + ' / ' + summary.formations, 'formations available'],
        [summary.reported_ammo, 'reported cartridges'],
        [summary.oldest_report_seconds + 's', 'oldest report'],
      ];
      $('analysis-basis').textContent = assessment.basis;
      $('analysis-summary').innerHTML = metrics.map(([value, label]) =>
        `<span><b>${esc(value)}</b>${label}</span>`).join('');
      const timing = replay ? 'recorded assessment' : state.clock?.running
        ? 'clock running · updates as reports arrive'
        : 'clock paused · assess before starting or at any time';
      const contacts = assessment.contacts.length ? assessment.contacts.map(contact =>
        `${contact.id}: ${contact.strength_range?.join('–') || 'unknown'} troops, ` +
        `${contact.confidence || 'uncertain'}, ${contact.age_seconds}s old`).join('; ')
        : 'No delivered enemy sightings.';
      $('analysis-context').textContent = `${clock(assessment.turn)} · ${timing}` +
        (godMode ? ' · headquarters knowledge only, even in God Mode' : '') + '. ' + contacts;
      $('analysis-limitations').textContent = assessment.limitations;
    }

    function renderRoster(assessment) {
      const label = id => assessment.standing_templates.find(template => template.id === id)?.label;
      $('analysis-roster').innerHTML = assessment.units.map(unit => {
        const metrics = [
          [`${unit.strength}/${unit.initial}`, 'troops'], [unit.volleys ?? '—', 'volleys available'],
          [unit.morale, 'morale /100'], [unit.fatigue, 'fatigue /100'], [unit.suppression, 'suppression /100'],
        ];
        const concerns = unit.concerns.length
          ? '<ul>' + unit.concerns.map(concern => `<li>${esc(concern)}</li>`).join('') + '</ul>'
          : '<p class="analysis-clear">No immediate condition concern in this report. Enemy pressure remains uncertain.</p>';
        return `<article class="analysis-unit ${unit.id === unitId ? 'selected' : ''}">
          <h3>${esc(unit.id)} · ${esc(unit.name)}</h3>
          <p>${esc(unit.role || 'line')} · ${esc(unit.weapons || 'unknown weapons')} · proficiency ${esc(unit.skill ?? 'unknown')}/100 · ${esc(unit.status)}</p>
          <div class="analysis-metrics">${metrics.map(([value, name]) => `<b>${esc(value)}<small>${name}</small></b>`).join('')}</div>
          <p>Observed ${clock(unit.observed_turn)} · received ${clock(unit.received_turn)} · ${unit.age_seconds}s old</p>
          <p>Mission: ${esc(unit.mission.replaceAll('_', ' '))}${unit.target ? ' → ' + unit.target.join(',') : ''} · Doctrine: ${esc(label(unit.standing_profile) || 'Legacy contact behavior')}</p>
          ${concerns}</article>`;
      }).join('');
    }

    function renderEditor(assessment, unit, state, busy, replay, godMode) {
      const templates = assessment.standing_templates;
      const label = id => templates.find(template => template.id === id)?.label;
      const units = assessment.units.map(row =>
        `<option value="${esc(row.id)}">${esc(row.id)} · ${esc(row.name)}</option>`).join('');
      const profiles = templates.map(template =>
        `<option value="${esc(template.id)}">${esc(template.label)}</option>`).join('');
      if ($('standing-unit').innerHTML !== units) $('standing-unit').innerHTML = units;
      if ($('standing-profile').innerHTML !== profiles) $('standing-profile').innerHTML = profiles;
      $('standing-unit').value = unitId;
      $('standing-profile').value = draft || unit.standing_profile || 'balanced';
      $('standing-intent').textContent = templates.find(template => template.id === $('standing-profile').value).intent;
      $('standing-current').textContent = 'Last reported: ' + (label(unit.standing_profile) || 'Legacy contact behavior') +
        (unit.standing_version !== null ? ' · version ' + unit.standing_version : '');
      $('standing-recommendation').textContent = 'Suggested: ' + label(unit.recommendation.profile_id) + '. ' + unit.recommendation.reason;

      const disabled = busy || replay || godMode || !['poc-8', 'poc-9', 'poc-10', 'poc-11', 'poc-12', 'poc-13'].includes(state.rules) || state.status !== 'active' ||
        !assessment.command_operational || ['routed', 'lost'].includes(unit.status);
      for (const id of ['standing-send', 'standing-recommend', 'standing-profile']) $(id).disabled = disabled;
      let status = 'Changing a selection is a draft. Dispatch sends it by voice or runner.';
      if (!['poc-8', 'poc-9', 'poc-10', 'poc-11', 'poc-12', 'poc-13'].includes(state.rules)) status = 'Use Reset to start a battle with configurable standing orders.';
      else if (godMode) status = 'Observer view: switch off God Mode to send instructions.';
      else if (replay) status = 'Recorded assessment; return to live to send instructions.';
      else if (!assessment.command_operational) status = 'Headquarters is disrupted. Existing standing orders continue.';
      else if (unit.pending_standing.length) status = unit.pending_standing.map(order =>
        `${order.id}: ${label(order.profile_id)} · awaiting acknowledgement`).join('; ');
      $('standing-status').textContent = status;
    }

    function render() {
      const {state, liveState, busy, replay, godMode} = context();
      if (!$('analysis-dialog').open || !state.analysis) return;
      const key = JSON.stringify([state.game_id, state.revision, unitId, draft, busy, replay, godMode, state.clock?.running]);
      if (renderKey === key) return;
      renderKey = key;
      const assessment = state.analysis;
      if (!assessment.units.some(unit => unit.id === unitId)) unitId = assessment.units[0]?.id;
      const unit = assessment.units.find(unit => unit.id === unitId);
      if (!unit) return;
      const scope = (state.game_id || liveState?.game_id) + ':' + unitId;
      if (draftScope !== scope) { draft = null; draftScope = scope; }
      renderSummary(assessment, state, replay, godMode);
      renderRoster(assessment);
      renderEditor(assessment, unit, state, busy, replay, godMode);
    }

    $('analysis-open').onclick = open;
    $('unit-analysis').onclick = open;
    $('analysis-close').onclick = () => $('analysis-dialog').close();
    $('standing-unit').onchange = () => {
      unitId = $('standing-unit').value;
      draft = null;
      render();
    };
    $('standing-profile').onchange = () => { draft = $('standing-profile').value; render(); };
    $('standing-recommend').onclick = () => {
      draft = context().state.analysis.units.find(unit => unit.id === unitId).recommendation.profile_id;
      render();
    };
    $('standing-form').onsubmit = async event => {
      event.preventDefault();
      if ($('standing-send').disabled) return;
      const result = await dispatch({unit_id: unitId, profile_id: $('standing-profile').value});
      if (result) toast('Standing instructions dispatched. The present mission continues.');
    };
    return Object.freeze({open, render});
  },
};
