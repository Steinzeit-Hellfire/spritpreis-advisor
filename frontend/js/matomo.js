// Lädt Matomo nur, wenn MATOMO_URL/MATOMO_SITE_ID in config.js gesetzt sind.
// Ohne config.js oder mit leeren Werten passiert einfach nichts - kein Tracking.
(function () {
  if (typeof MATOMO_URL === "undefined" || !MATOMO_URL) return;
  if (typeof MATOMO_SITE_ID === "undefined" || !MATOMO_SITE_ID) return;

  var _paq = (window._paq = window._paq || []);
  _paq.push(["trackPageView"]);
  _paq.push(["enableLinkTracking"]);
  (function () {
    var u = MATOMO_URL.endsWith("/") ? MATOMO_URL : MATOMO_URL + "/";
    _paq.push(["setTrackerUrl", u + "matomo.php"]);
    _paq.push(["setSiteId", MATOMO_SITE_ID]);
    var d = document,
      g = d.createElement("script"),
      s = d.getElementsByTagName("script")[0];
    g.async = true;
    g.src = u + "matomo.js";
    s.parentNode.insertBefore(g, s);
  })();

  // Einfaches Fehler-Tracking als Custom Event. Kein Ersatz für ein
  // dediziertes Tool wie GlitchTip, aber zeigt grobe Fehlerhäufungen an.
  window.addEventListener("error", function (ev) {
    _paq.push(["trackEvent", "JS-Fehler", ev.message || "unbekannt", `${ev.filename}:${ev.lineno}`]);
  });
})();
