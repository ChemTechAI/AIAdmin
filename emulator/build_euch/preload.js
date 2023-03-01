const { contextBridge, ipcRenderer } = require("electron");

const electronLogger = require("electron-log");
electronLogger.transports.file.file = "ai_operator.log";
electronLogger.transports.file.maxSize = 1048576 * 100;

const Store = require("electron-store");
const store = new Store();
const proxy = store.get("proxy");

contextBridge.exposeInMainWorld("api", {
  send: (channel, data) => {
    let validChannels = ["appExit", "appCollapse", "appShow", "asynchronous-message"];
    if (validChannels.includes(channel)) {
      ipcRenderer.send(channel, data);
    }
  },
  receive: (channel, func) => {
    let validChannels = ["fromMain", "asynchronous-reply"];
    if (validChannels.includes(channel)) {
      ipcRenderer.on(channel, (event, ...args) => func(...args));
    }
  },
  log: electronLogger,
  endpoint: `${proxy.protocol}://${proxy.host}:${proxy.port}/`,
});
