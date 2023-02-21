const fetch = require("node-fetch");

function combineURL({ protocol, host, port }) {
  return `${protocol}://${host}:${port}`;
}

function waitServer(proxy, mainWindow, log) {
  fetch(combineURL(proxy))
    .then(() =>
      mainWindow.create(
        "AI Operator",
        false,
        false,
        true,
        "index.html",
        "http://localhost:3000"
      )
    )
    .catch((err) => {
      log.error("Wait server response...", err.message);
      setTimeout(() => waitServer(proxy, mainWindow, log), 3000);
    });
}

module.exports = {
  waitServer,
};
