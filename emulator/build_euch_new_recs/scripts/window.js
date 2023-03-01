const path = require("path");

class Window {
  constructor(electron, dir, isDev, logger) {
    this._electron = electron;
    this._dir = dir;
    this._isDev = isDev;
    this._log = logger;
    this.window = null;
  }

  isActive() {
    return this.window;
  }

  init(title, show, modal, preload) {
    return new this._electron.BrowserWindow({
      fullscreen: !modal,
      frame: modal,
      resizable: modal,
      title: title,
      backgroundColor: "#212121",
      show: show,
      webPreferences: {
        nodeIntegration: false,
        contextIsolation: true,
        enableRemoteModule: false,
        preload: preload ? path.join(this._dir, "preload.js") : null,
      },
    });
  }

  chooseSource(src, srcDev) {
    const prodSource = this.combinePath(src);
    const devSource = srcDev ? srcDev : prodSource;

    return this._isDev ? devSource : prodSource;
  }

  combinePath(src) {
    return `file://${path.join(this._dir, src)}`;
  }

  runOnHighResScreen(window, modal) {
    if (!this._isDev || modal) return;

    const { screen } = this._electron;
    if (screen.getAllDisplays().length > 1) {
      const allDisplays = screen.getAllDisplays();
      const maxResDisplay = allDisplays.reduce((prev, current) =>
        prev.bounds.width > current.bounds.width ? prev : current
      );

      window.setBounds(maxResDisplay.workArea);
      window.setPosition(maxResDisplay.bounds.x, maxResDisplay.bounds.y);
    }
  }

  loadSource(window, src, srcDev, modal) {
    window
      .loadURL(this.chooseSource(src, srcDev))
      .then(() => this.runOnHighResScreen(window, modal))
      .catch((err) => this._log.error(`(${src})window creation error!`, err.message));
  }

  create(title, modal, show, preload, src, srcDev) {
    if (this.isActive()) {
      this._log.errorBox("Second instance error!", `${title} instance already running`);
    } else {
      this.window = this.init(title, show, modal, preload);
      this.loadSource(this.window, src, srcDev, modal);
      // this.window.removeMenu();
      this.window.on("closed", () => (this.window = null));
    }
  }

  focus() {
    if (this.isActive()) return this.window.focus();
  }

  restore() {
    if (this.isActive()) return this.window.restore();
  }

  isMinimized() {
    if (this.isActive()) return this.window.isMinimized();
  }

  show() {
    if (this.isActive()) this.window.show();
  }

  destroy() {
    if (this.isActive()) this.window.destroy();
  }

  reload() {
    if (this.isActive()) this.window.reload();
  }

  minimize() {
    if (this.isActive()) this.window.minimize();
  }

  ipcSend(channel, data) {
    if (this.isActive()) this.window.webContents.send(channel, data);
  }
}

module.exports = Window;
