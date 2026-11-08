/* bt-T11: order wording from the viewing side's own communications profile.
 * Reads only `command.profile` (label, methods, reach flags) from the commander view;
 * never an order's transport, which only God Mode carries. The server's dispatch
 * templates are recorded state and keep their own wording. */
const BattleOrderWording = (() => {
  const SIGNAL = /signal|trumpet/i;
  // A view with no command profile is a legacy headquarters; its orders went by runner.
  const LEGACY = Object.freeze(['runner']);

  /* What: the period names of the means that carry an order, in the profile label's order
   * ("1944 · radio / voice / runner" -> radio, voice, runner). A trumpet signal is a separate
   * broadcast, not an order carrier, so it is left out. Voice carries an order to another
   * unit only when the profile has a voice reach; with `local` (an order that may go to the
   * command's own detachment) voice is always kept. */
  function means(profile, {local = false} = {}) {
    const label = typeof profile?.label === 'string' ? profile.label : '';
    const methods = Array.isArray(profile?.methods) ? profile.methods : [];
    if (!label.includes(' · ')) return [...LEGACY];
    const parts = label.slice(label.indexOf(' · ') + 3).split(' / ').map(part => part.trim()).filter(Boolean);
    const reach = Boolean(profile.voice_reach || profile.voice_reach_from_entry);
    const kept = parts.filter(part => !(methods.includes('signal') && SIGNAL.test(part)) &&
      (local || reach || part !== 'voice'));
    return kept.length ? kept : [...LEGACY];
  }

  // "a", "a or b", "a, b or c".
  function list(words) {
    return words.length < 2 ? words.join('') : `${words.slice(0, -1).join(', ')} or ${words.at(-1)}`;
  }

  // The send button for an order to a detachment other than the command's own.
  const send = profile => `Dispatch by ${list(means(profile))} ↗`;
  // Its tooltip: the profile's label and every means an order can take.
  const tooltip = profile => profile?.label
    ? `${profile.label}: orders go by ${list(means(profile))}${means(profile).length > 1 ? ', as distance allows' : ''}.`
    : `Orders go by ${list(means(profile))}.`;
  // The mission panel's help line.
  const help = profile => `Movement orders travel by ${list(means(profile))}.`;
  // The map tip once a destination is chosen.
  const tip = profile => `dispatch by ${list(means(profile))}`;
  // Standing orders may go to the command's own detachment, so voice stays in.
  const standing = profile => `Changing a selection is a draft. Dispatch sends it by ${list(means(profile, {local: true}))}.`;

  return Object.freeze({means, list, send, tooltip, help, tip, standing});
})();
