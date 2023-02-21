const electron = require("electron");
electron.app.commandLine.appendSwitch("force-color-profile", "srgb");

const isDev = require("electron-is-dev");
const Store = require("electron-store");

const config = require("./scripts/config.json");
const Logger = require("./scripts/logger.js");
const Window = require("./scripts/window.js");
const utils = require("./scripts/utils.js");
const ModuleWorker = require("./scripts/moduleWorker.js");

const store = new Store(config.store);
const log = new Logger(store, process, electron);
log.appInfo();

let mainWindow = new Window(electron, __dirname, isDev, log);
let loadingWindow = new Window(electron, __dirname, isDev, log);
let terminalWindow = new Window(electron, __dirname, isDev, log);
const moduleWorker = new ModuleWorker(isDev, store.get("startup.modules"), terminalWindow, log);

function registerShortcuts() {
  electron.globalShortcut.register("CommandOrControl+R", () => mainWindow.reload());
  electron.globalShortcut.register("CommandOrControl+Shift+Alt+T", () => {
    terminalWindow.create("Terminal", true, true, true, "terminal.html", null);
  });
}

electron.app.on("ready", () => {
  loadingWindow.create("Loading...", false, true, false, "splash.html", null);
  moduleWorker.runAll();
  utils.waitServer(store.get("proxy"), mainWindow, log);
  registerShortcuts();

  setTimeout(() => {
    if (loadingWindow.isActive() && !isDev) {
      loadingWindow.destroy();
      mainWindow.destroy();
      electron.app.quit();
      log.errorBox(``, "Server refused connection(timeout).");
    }
  }, 60000);
});

electron.ipcMain.on("appShow", () => {
  mainWindow.show();
  loadingWindow.destroy();
});

electron.ipcMain.on("appCollapse", () => {
  mainWindow.minimize();
});

electron.ipcMain.on("appExit", () => {
  mainWindow.destroy();
  electron.app.quit();
  // killModules(store.get("startup.modules"));
});

if (!electron.app.requestSingleInstanceLock()) {
  electron.app.quit();
} else {
  electron.app.on("second-instance", () => {
    if (mainWindow) {
      if (mainWindow.isMinimized()) mainWindow.restore();
      mainWindow.focus();
    }
  });
}
