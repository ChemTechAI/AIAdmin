class Logger {
  constructor(store, process, electron) {
    this._store = store;
    this._process = process;
    this._electron = electron;
  }

  drawLogo() {
    console.log(
      "" +
        "   ________                 ______          __\n" +
        "  / ____/ /_  ___  ____ ___/_  __/__  _____/ /_\n" +
        " / /   / __ \\/ _ \\/ __ `__ \\/ / / _ \\/ ___/ __ \\\n" +
        "/ /___/ / / /  __/ / / / / / / /  __/ /__/ / / /\n" +
        "\\____/_/ /_/\\___/_/ /_/ /_/_/  \\___/\\___/_/ /_/\n"
    );
  }

  procInfo() {
    console.log(this._process.versions);
  }

  appStoreProp(prop) {
    console.log(`\nApp config ${prop}:`);
    console.log(this._store[prop]);
  }

  errorBox(title, message) {
    this._electron.dialog.showErrorBox(title, message);
  }

  error(title, message, dialog = false) {
    console.error("\n" + title);
    console.error(message);

    if (dialog) this.errorBox(title, message);
  }

  appInfo() {
    this.drawLogo();
    this.procInfo();
    this.appStoreProp("path");
  }
}

module.exports = Logger;
