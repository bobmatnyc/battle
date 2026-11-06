/* Scenario-local calendar formatting. UTC is a neutral calendar arithmetic
 * frame here, not a claim that the battle's local time was UTC. */
const BattleTimeline = (() => {
  function instant(setting, elapsedSeconds) {
    return new Date(Date.parse(setting.start_local + 'Z') + elapsedSeconds * 1000);
  }

  function time(setting, elapsedSeconds, locale = 'en-GB') {
    const value = instant(setting, elapsedSeconds);
    return new Intl.DateTimeFormat(locale, {
      timeZone: 'UTC', hour: '2-digit', minute: '2-digit',
      ...(value.getUTCSeconds() ? {second: '2-digit'} : {}), hourCycle: 'h23',
    }).format(value);
  }

  function date(setting, elapsedSeconds, locale = 'en-GB') {
    return new Intl.DateTimeFormat(locale, {
      timeZone: 'UTC', weekday: 'long', day: 'numeric', month: 'long', year: 'numeric',
    }).format(instant(setting, elapsedSeconds));
  }

  return Object.freeze({time, date});
})();
