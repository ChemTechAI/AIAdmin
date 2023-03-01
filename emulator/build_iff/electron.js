const electron = require('electron');
const app = electron.app;
const ipcMain = electron.ipcMain;
const globalShortcut = electron.globalShortcut;
const BrowserWindow = electron.BrowserWindow;
const dialog = electron.dialog;
app.commandLine.appendSwitch('force-color-profile', 'srgb');

const path = require('path');
const find = require('find-process');
const processExec = require('child_process');
const isDev = require('electron-is-dev');
const fetch = require('node-fetch');

let mainWindow;
let loadingWindow;

const PORT = 8085;
const URL_HANDLER = {
  '/recommendations': function (params) {
    mainWindow.webContents.send('newRecProps', params);
  },
};

function createWindow() {
  globalShortcut.register('Ctrl+Alt+1', () =>
    mainWindow.webContents.send('newRecProps', {
      id: 'rec#1',
      text: 'Please set FT101E = ',
      observed_tag: 'FT101E_opt',
      workspaceId: 'M100',
      units: ' kg/m',
      precision: 1,
      priority: 2,
      diff: 1.5,
    })
  );
  globalShortcut.register('Ctrl+Alt+2', () =>
    mainWindow.webContents.send('newRecProps', {
      id: 'rec#2',
      text: 'Please set MF102 = ',
      observed_tag: 'MF102_opt',
      workspaceId: 'M100',
      units: ' kg/m',
      precision: 1,
      priority: 4,
      diff: 0.25,
    })
  );
  globalShortcut.register('Ctrl+R', () => mainWindow.reload());

  mainWindow = new BrowserWindow({
    fullscreen: true,
    frame: false,
    resizable: false,
    title: 'AI Operator',
    backgroundColor: '#212121',
    show: false,
    webPreferences: {
      nodeIntegration: true,
      backgroundThrottling: true,
    },
  });
  mainWindow.loadURL(
    isDev
      ? 'http://localhost:3000'
      : `file://${path.join(__dirname, '../build/index.html')}`
  );
  mainWindow.on('closed', () => (mainWindow = null));
}

function createLoadingWindow() {
  loadingWindow = new BrowserWindow({
    fullscreen: true,
    frame: false,
    resizable: false,
    title: 'AI Operator',
    backgroundColor: '#212121',
  });
  loadingWindow.loadURL(
    isDev
      ? `file://${path.join(__dirname, 'splash.html')}`
      : `file://${path.join(__dirname, '../build/splash.html')}`
  );
}

function createLocalServer() {
  let http = require('http');
  let server = http.createServer(function (req, res) {
    let route = req.url.split(/[?#]/)[0];
    console.log(`Got request on: ${route}`);
    if (Object.keys(URL_HANDLER).includes(route)) {
      let queryData = '';
      req.on('data', (chunk) => {
        queryData += chunk;
      });
      req.on('end', () => {
        URL_HANDLER[route](JSON.parse(queryData));
      });
      res.statusCode = 200;
    } else {
      res.statusCode = 400;
    }
    res.end();
  });
  server.listen(PORT);
  console.log('Local server running on: http://localhost:' + PORT);
}

async function backEndCheck() {
  return checkSubProcRunStatus('engine');
}

async function checkSubProcRunStatus(name) {
  let isOpened = false;

  await find('name', 'ai_' + name).then(
    function (list) {
      if (list.length) {
        isOpened = true;
      } else {
        runBackEndProcess(name);
      }
    },
    function (err) {}
  );

  return isOpened;
}

function runBackEndProcess(name) {
  try {
    const sub = processExec.spawn(`${name}.bat`, [], {
      cwd: './engine',
      detached: true,
      stdio: 'ignore',
      shell: false,
      windowsHide: true,
    });

    sub.unref();
    console.log('waiting..');
  } catch (err) {
    console.log(err);
  }
}

function killBackEnd() {
  killProcessByName('ai_engine');
}

function killProcessByName(name) {
  processExec.exec(
    `taskkill /IM "${name}.exe" /F`,
    function (err, stdout, stderr) {
      if (err) dialog.showErrorBox(`${name} kill error.`, stderr);
    }
  );
}

async function addDevTools() {
  const session = electron.session;
  const homeDir = require('os').homedir();
  const chromeExtensions = `\\AppData\\Local\\Google\\Chrome\\User Data\\Default\\Extensions`;
  const reactExtension = `\\fmkadmapgofadopljbjfkapdkoienihi\\4.13.5_0`;
  const reduxExtension = `\\lmhkpmbekcpmknklioeibfkpmmfibljd\\2.17.2_0`;
  await session.defaultSession.loadExtension(
    homeDir + chromeExtensions + reactExtension
  );
  await session.defaultSession.loadExtension(
    homeDir + chromeExtensions + reduxExtension
  );
}

function waitServer(address) {
  fetch(address)
    .then(() => {
      createWindow();
    })
    .catch((err) => {
      console.error('Wait server response...', err.message);
      setTimeout(() => waitServer(address), 3000);
    });
}

function errorAppExit(error = null) {
  if (loadingWindow) loadingWindow.destroy();
  if (mainWindow) mainWindow.destroy();
  electron.app.quit();
  if (error) electron.dialog.showErrorBox(``, error);
}

app.on('ready', async () => {
  if (isDev) addDevTools();

  createLoadingWindow();

  createLocalServer();

  await backEndCheck();

  waitServer(`http://localhost:5051`);

  setTimeout(() => {
    if (loadingWindow) errorAppExit('Server refused connection(timeout).');
  }, 90000);
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

ipcMain.on('show', () => {
  mainWindow.show();
  if (loadingWindow) {
    loadingWindow.destroy();
    loadingWindow = null;
  }
});

ipcMain.on('collapse', () => {
  mainWindow.minimize();
});

ipcMain.on('exit', () => {
  killBackEnd();
  app.quit();
});

const gotTheLock = app.requestSingleInstanceLock();
if (!gotTheLock) {
  app.quit();
} else {
  app.on('second-instance', (event, cmdLine, workDir) => {
    if (mainWindow) {
      if (mainWindow.isMinimized()) mainWindow.restore();
      mainWindow.focus();
    }
  });
}
