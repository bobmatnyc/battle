/* Scenario choice for the next battle. Receives the element lookup, the catalog
 * loader and a context reader; it never touches the network itself. */
const ScenarioPicker = {
  create({element, esc, load, context}) {
    let catalog = [], chosen = null;
    const select = () => element('scenario-select');
    select().onchange = () => { chosen = select().value || null; };
    const currentId = () => context().state?.scenario_brief?.id || null;
    return Object.freeze({
      async init() {
        catalog = (await load()).scenarios || [];
        this.render();
      },
      render() {
        const wanted = chosen ?? currentId();
        const options = catalog.map(s => `<option value="${esc(s.id)}">${esc(s.title)}</option>`).join('');
        if (select().innerHTML !== options) select().innerHTML = options;  // Keep an open list open.
        if (catalog.some(s => s.id === wanted)) select().value = wanted;
        select().disabled = catalog.length < 2;
      },
      // The scenario Reset starts: the player's pick, else the one being played.
      selected() { return chosen ?? currentId(); },
      reset() { chosen = null; this.render(); },
    });
  },
};
